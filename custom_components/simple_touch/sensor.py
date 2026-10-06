"""Bridge diagnostics, sharing the existing local coordinator poll."""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

SENSORS = (
    SensorEntityDescription(key="wifi_rssi", name="Wi-Fi signal", device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="ip", name="IP address", icon="mdi:ip-network"),
    SensorEntityDescription(key="uptime_s", name="Uptime", device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES),
    SensorEntityDescription(key="reset_reason", name="Reset reason", icon="mdi:restart"),
    SensorEntityDescription(key="update_state", name="Update status", icon="mdi:update"),
    SensorEntityDescription(key="rx_overflows", name="Radio FIFO overflows", icon="mdi:counter", entity_registry_enabled_default=False),
    SensorEntityDescription(key="rx_queue_drops", name="Radio queue drops", icon="mdi:counter", entity_registry_enabled_default=False),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BridgeSensor(coordinator, description) for description in SENSORS])


class BridgeSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, description):
        super().__init__(coordinator)
        self.entity_description = description
        device = coordinator.data["device_id"]
        self._attr_unique_id = f"{device}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device)}, name="Simple Touch Bridge")

    @property
    def available(self):
        return super().available and self.coordinator.data.get(self.entity_description.key) is not None

    @property
    def native_value(self):
        value = self.coordinator.data.get(self.entity_description.key)
        return int(value // 60) if self.entity_description.key == "uptime_s" and value is not None else value

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "update_state":
            return {key: self.coordinator.data.get(key) for key in
                    ("update_error", "update_received_bytes", "update_expected_bytes", "restart_pending")}
        return None
