"""Connect to a bridge without YAML or a cloud account."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BridgeApi, BridgeAuthError, BridgeError, normalize_host
from .const import CONF_HOST, CONF_KEY, DOMAIN


def schema(host=""):
    return vol.Schema({vol.Required(CONF_HOST, default=host): str,
                       vol.Required(CONF_KEY): selector.TextSelector(
                           selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            try:
                host = normalize_host(user_input[CONF_HOST])
                data = await BridgeApi(async_get_clientsession(self.hass), host, user_input[CONF_KEY]).state()
                await self.async_set_unique_id(data["device_id"])
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(title=data.get("name", "Simple Touch"),
                                              data={CONF_HOST: host, CONF_KEY: user_input[CONF_KEY]})
            except BridgeAuthError:
                errors["base"] = "invalid_auth"
            except (BridgeError, ValueError):
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="user", data_schema=schema(), errors=errors)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        entry = self._get_reauth_entry()
        return await self._update_entry(entry, "reauth_confirm", user_input)

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        return await self._update_entry(entry, "reconfigure", user_input)

    async def _update_entry(self, entry, step, user_input):
        errors = {}
        if user_input:
            try:
                host = normalize_host(user_input[CONF_HOST])
                data = await BridgeApi(async_get_clientsession(self.hass), host, user_input[CONF_KEY]).state()
                if data["device_id"] != entry.unique_id:
                    errors["base"] = "wrong_bridge"
                else:
                    return self.async_update_reload_and_abort(entry, data_updates={CONF_HOST: host, CONF_KEY: user_input[CONF_KEY]})
            except BridgeAuthError:
                errors["base"] = "invalid_auth"
            except (BridgeError, ValueError):
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id=step, data_schema=schema(entry.data[CONF_HOST]), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}),
                                   description_placeholders={"url": self._entry.data[CONF_HOST]})
