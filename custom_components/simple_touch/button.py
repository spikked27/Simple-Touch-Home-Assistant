"""Recall the motor's saved favorite position."""
from homeassistant.components.button import ButtonEntity
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
                entities.append(FavoriteButton(coordinator, remote["id"]))
        if entities:
            async_add_entities(entities)

    entry.async_on_unload(coordinator.async_add_listener(discover))
    discover()


class FavoriteButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Favorite position"
    _attr_icon = "mdi:star-outline"

    def __init__(self, coordinator, remote_id):
        super().__init__(coordinator)
        self.remote_id = remote_id
        device = f"{coordinator.data['device_id']}_{remote_id}"
        self._attr_unique_id = device + "_favorite"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device)},
                                           name=self.remote.get("name", "Shade"),
                                           configuration_url=coordinator.api.host)

    @property
    def remote(self):
        return next((r for r in self.coordinator.data.get("remotes", []) if r["id"] == self.remote_id), {})

    @property
    def available(self):
        return (super().available and self.remote.get("paired", False)
                and self.coordinator.data.get("radio_ready", False)
                and self.coordinator.data.get("favorite_supported", False))

    async def async_press(self):
        try:
            result = await self.coordinator.api.command(self.remote_id, "favorite")
        except BridgeError as err:
            raise HomeAssistantError(str(err)) from err
        data = dict(self.coordinator.data)
        data["remotes"] = [dict(r, **result.get("remote", {"last_command": "favorite", "state_source": "bridge", "assumed_state": "favorite"})) if r["id"] == self.remote_id else r
                           for r in data["remotes"]]
        self.coordinator.async_set_updated_data(data)
