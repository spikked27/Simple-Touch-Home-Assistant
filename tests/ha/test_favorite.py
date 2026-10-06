"""Favorite targets cover entities without exposing percentage control."""
from unittest.mock import patch
import pytest
from homeassistant.components.cover import CoverEntityFeature
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_favorite_action(hass, enable_custom_integrations):
    from custom_components.simple_touch.api import BridgeError
    remotes = [dict(id=identity, name=name, paired=True, assumed_state="open")
               for identity, name in [("12345600", "First"), ("789abc00", "Second")]]
    inventory = dict(api_version=1, device_id="001122334455", version="1.1.0",
                     radio_ready=True, remotes=remotes)
    entry = MockConfigEntry(domain="simple_touch", unique_id=inventory["device_id"],
                            data={"host": "http://192.0.2.10", "api_key": "test-only"})
    entry.add_to_hass(hass)
    with patch("custom_components.simple_touch.api.BridgeApi.state", return_value=inventory), \
         patch("custom_components.simple_touch.api.BridgeApi.command", return_value={}) as command, \
         patch("custom_components.simple_touch.update.latest_release", side_effect=BridgeError):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        covers = hass.states.async_all("cover")
        assert len(covers) == 2
        await hass.services.async_call("simple_touch", "favorite", {
            "entity_id": [cover.entity_id for cover in covers]}, blocking=True)
        assert command.await_count == 2
        assert {call.args for call in command.await_args_list} == {
            ("12345600", "favorite"), ("789abc00", "favorite")}
        for cover in covers:
            current = hass.states.get(cover.entity_id)
            assert current.state == "open"
            assert current.attributes["assumed_position"] == "favorite"
            assert current.attributes["last_command"] == "favorite"
            assert "current_position" not in current.attributes
            assert not current.attributes["supported_features"] & CoverEntityFeature.SET_POSITION
        await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(("position", "ready", "expected"), [
    ("favorite", True, "open"), ("unknown", True, "open"),
    ("partial", True, "open"), ("closed", True, "closed"),
    ("opening", True, "opening"), ("closing", True, "closing"),
    ("favorite", False, "unavailable"), ("unknown", False, "unavailable"),
])
async def test_assumed_cover_state(hass, enable_custom_integrations, position, ready, expected):
    from custom_components.simple_touch.api import BridgeError
    remote = dict(id="12345600", name="Test", paired=True, assumed_state=position)
    inventory = dict(api_version=1, device_id="001122334455", version="1.1.1",
                     radio_ready=ready, remotes=[remote])
    entry = MockConfigEntry(domain="simple_touch", unique_id=inventory["device_id"],
                            data={"host": "http://192.0.2.10", "api_key": "test-only"})
    entry.add_to_hass(hass)
    with patch("custom_components.simple_touch.api.BridgeApi.state", return_value=inventory), \
         patch("custom_components.simple_touch.update.latest_release", side_effect=BridgeError):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        cover = hass.states.async_all("cover")[0]
        assert cover.state == expected
        if ready:
            assert cover.attributes["assumed_position"] == position
        assert "current_position" not in cover.attributes
        assert not cover.attributes["supported_features"] & CoverEntityFeature.SET_POSITION
        await hass.config_entries.async_unload(entry.entry_id)

