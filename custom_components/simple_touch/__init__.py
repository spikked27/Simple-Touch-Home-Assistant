"""Native Home Assistant entities for the local Simple Touch bridge."""
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import service
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BridgeApi, BridgeAuthError, BridgeError
from .const import CONF_HOST, CONF_KEY, DOMAIN

PLATFORMS = [Platform.COVER, Platform.BUTTON, Platform.UPDATE, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup(hass: HomeAssistant, config) -> bool:
    service.async_register_platform_entity_service(
        hass, DOMAIN, "favorite", entity_domain=Platform.COVER,
        schema={}, func="async_favorite_position",
    )
    return True


class BridgeCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        import logging
        super().__init__(hass, logging.getLogger(__name__), name=DOMAIN,
                         update_interval=timedelta(seconds=1))
        self.api = BridgeApi(async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_KEY])
        self.maintenance = False

    async def _async_update_data(self):
        # Avoid a queue of inventory requests competing with a firmware upload.
        if self.maintenance:
            return self.data
        try:
            return await self.api.state()
        except BridgeAuthError as err:
            raise ConfigEntryAuthFailed from err
        except BridgeError as err:
            raise UpdateFailed(str(err)) from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = BridgeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return True
    return False
