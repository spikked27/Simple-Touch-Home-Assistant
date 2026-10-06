"""Report radio initialization problems separately from shade position."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RadioProblem(hass.data[DOMAIN][entry.entry_id])])


class RadioProblem(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Radio problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator)
        device = coordinator.data["device_id"]
        self._attr_unique_id = f"{device}_radio_problem"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device)}, name="Simple Touch Bridge")

    @property
    def is_on(self):
        value = self.coordinator.data.get("radio_ready")
        return None if value is None else not value
