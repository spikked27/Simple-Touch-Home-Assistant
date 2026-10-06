"""Diagnostics exclude bridge keys, network addresses and remote addresses."""
from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    data = hass.data[DOMAIN][entry.entry_id].data
    return {"version": data.get("version"), "api_version": data.get("api_version"),
            "radio_ready": data.get("radio_ready"), "frequency_hz": data.get("frequency_hz"),
            "remote_count": len(data.get("remotes", []))}
