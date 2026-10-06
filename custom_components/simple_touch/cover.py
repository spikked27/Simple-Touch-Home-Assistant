"""One cover entity per paired virtual remote. No fabricated motor position."""
from homeassistant.components.cover import CoverDeviceClass, CoverEntity, CoverEntityFeature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BridgeError
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    known = set()

    def discover():
        entities = []
        for remote in coordinator.data.get("remotes", []):
            if remote.get("paired") and remote["id"] not in known:
                known.add(remote["id"])
                entities.append(SimpleTouchCover(coordinator, remote["id"]))
        if entities:
            async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(discover))
    discover()


class SimpleTouchCover(CoordinatorEntity, CoverEntity):
    _attr_device_class = CoverDeviceClass.SHADE
    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    _attr_supported_features = (CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP)

    def __init__(self, coordinator, remote_id):
        super().__init__(coordinator)
        self.remote_id = remote_id
        bridge = coordinator.data["device_id"]
        self._attr_unique_id = f"{bridge}_{remote_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self.remote.get("name", "Shade"), manufacturer="Simple Touch community",
            model="Virtual RF remote", configuration_url=coordinator.api.host,
            sw_version=coordinator.data.get("version"),
        )

    @property
    def remote(self):
        return next((r for r in self.coordinator.data.get("remotes", []) if r["id"] == self.remote_id), {})

    @property
    def available(self):
        return super().available and self.coordinator.data.get("radio_ready", False) and self.remote.get("paired", False)

    @property
    def is_closed(self):
        command = self.remote.get("last_command")
        return True if command == "down" else False if command == "up" else None

    @property
    def current_cover_position(self):
        return None

    @property
    def extra_state_attributes(self):
        return {"last_command": self.remote.get("last_command", "unknown"), "position_feedback": False,
                "state_source": self.remote.get("state_source", "unknown"), "state_is_assumed": True}

    async def _command(self, action):
        try:
            await self.coordinator.api.command(self.remote_id, action)
        except BridgeError as err:
            raise HomeAssistantError(str(err)) from err
        # Update immediately, without waiting for the periodic inventory refresh.
        data = dict(self.coordinator.data)
        data["remotes"] = [dict(r, last_command=action, state_source="bridge") if r["id"] == self.remote_id else r
                           for r in data["remotes"]]
        self.coordinator.async_set_updated_data(data)

    async def async_open_cover(self, **kwargs):
        await self._command("up")

    async def async_close_cover(self, **kwargs):
        await self._command("down")

    async def async_stop_cover(self, **kwargs):
        await self._command("stop")
