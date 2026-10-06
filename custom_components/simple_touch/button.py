"""Recall the motor's saved favorite position."""
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BridgeError, BridgeRestartUncertain
from .const import DOMAIN
from .maintenance import wait_for_restart


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RestartButton(coordinator)])
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


class RestartButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Restart"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator)
        device = coordinator.data["device_id"]
        self._attr_unique_id = f"{device}_restart"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device)}, name="Simple Touch Bridge")

    @property
    def available(self):
        return super().available and not self.coordinator.maintenance

    async def async_press(self):
        if self.coordinator.maintenance:
            raise HomeAssistantError("The bridge is already updating or restarting")
        self.coordinator.maintenance = True
        try:
            before = await self.coordinator.api.status()
            try:
                await self.coordinator.api.restart()
            except BridgeRestartUncertain:
                # A restart may close the connection before its response arrives.
                pass
            status = await wait_for_restart(self.coordinator.api, before)
            data = dict(self.coordinator.data, **status)
            try:
                data = await self.coordinator.api.state()
            except BridgeError:
                pass  # Boot is confirmed; normal polling will refresh inventory.
            self.coordinator.async_set_updated_data(data)
        except BridgeError as err:
            raise HomeAssistantError(str(err)) from err
        finally:
            self.coordinator.maintenance = False
            self.async_write_ha_state()
