"""Native Home Assistant firmware update availability and installation."""
import asyncio
from datetime import timedelta
import time

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity, UpdateEntityFeature
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BridgeError, BridgeUpdateUncertain
from .const import DOMAIN
from .firmware import download_release, latest_release

SCAN_INTERVAL = timedelta(hours=1)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([BridgeFirmware(hass.data[DOMAIN][entry.entry_id])], True)


class BridgeFirmware(CoordinatorEntity, UpdateEntity):
    _attr_has_entity_name = True
    _attr_name = "Firmware"
    _attr_title = "Simple Touch bridge firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_features = UpdateEntityFeature.INSTALL
    _attr_should_poll = True
    _attr_release_url = "https://github.com/spikked27/Simple-Touch-Home-Assistant/blob/main/docs/testing.md"
    _attr_release_summary = "Update the bridge firmware while preserving shades, linked remotes and Wi-Fi settings. The bridge will briefly restart."

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.release = None
        self._attr_unique_id = f"{coordinator.data['device_id']}_firmware"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.data['device_id'])},
            name="Simple Touch Bridge", manufacturer="Simple Touch community", model="XIAO ESP32-S3 / CC1101",
            configuration_url=coordinator.api.host)

    @property
    def installed_version(self):
        return self.coordinator.data.get("version")

    @property
    def available(self):
        return super().available and self.release is not None

    async def async_update(self):
        if self.in_progress:
            return
        try:
            self.release = await latest_release(async_get_clientsession(self.hass))
            self._attr_latest_version = self.release["version"]
        except BridgeError:
            # An internet outage must not affect local shade control.
            self.release = None
            self._attr_latest_version = None

    async def async_install(self, version, backup, **kwargs):
        if self.in_progress:
            raise HomeAssistantError("A firmware update is already running")
        if not self.release or not self.version_is_newer(self.release['version'], self.installed_version):
            raise HomeAssistantError("No newer firmware update is available")
        if version is not None and version != self.release['version']:
            raise HomeAssistantError("Only the advertised firmware version can be installed")
        if backup:
            raise HomeAssistantError("Export a remote backup in Bridge settings before updating")
        release = dict(self.release)
        self._attr_in_progress = True
        self.async_write_ha_state()
        try:
            image = await download_release(async_get_clientsession(self.hass), release)
            try:
                await self.coordinator.api.upload_firmware(image, release['sha256'])
            except BridgeUpdateUncertain:
                pass  # Never send the upload again; verify whether it succeeded.
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                await asyncio.sleep(2)
                try:
                    state = await self.coordinator.api.state()
                    if state.get('version') == release['version']:
                        self.coordinator.async_set_updated_data(state)
                        return
                except BridgeError:
                    continue
            raise BridgeError("Update not confirmed. Check bridge power and Wi-Fi, then its installed version before retrying.")
        except BridgeError as err:
            raise HomeAssistantError(str(err)) from err
        finally:
            self._attr_in_progress = False
            self.async_write_ha_state()
