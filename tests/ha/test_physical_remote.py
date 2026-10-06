"""Physical Stop updates a real HA cover without waiting for travel expiry."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.asyncio
async def test_physical_stop_on_next_poll(hass, enable_custom_integrations):
    from custom_components.simple_touch.api import BridgeError
    remote = dict(id="12345600", name="Test shade", paired=True, last_command="down",
                  assumed_state="closing", state_source="physical_remote", travel_time_s=60)
    inventory = dict(api_version=1, device_id="001122334455", version="0.4.0",
                     radio_ready=True, remotes=[remote])
    entry = MockConfigEntry(domain="simple_touch", unique_id=inventory["device_id"],
                            data={"host": "http://192.0.2.10", "api_key": "test-only"})
    entry.add_to_hass(hass)
    with patch("custom_components.simple_touch.api.BridgeApi.state", return_value=inventory) as state, \
         patch("custom_components.simple_touch.update.latest_release", side_effect=BridgeError):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        cover = hass.states.async_all("cover")[0]
        assert cover.state == "closing"
        state.return_value = dict(inventory, remotes=[dict(remote, last_command="stop", assumed_state="partial")])
        # A poll must consume physical state long before the 60-second travel window.
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2))
        await hass.async_block_till_done()
        stopped = hass.states.get(cover.entity_id)
        assert stopped.state == "open"
        assert stopped.attributes["assumed_position"] == "partial"
        assert stopped.attributes["last_command"] == "stop"
        assert stopped.attributes["state_source"] == "physical_remote"
        assert "current_position" not in stopped.attributes
        await hass.config_entries.async_unload(entry.entry_id)
