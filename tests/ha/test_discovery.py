"""Discovery through Home Assistant's real flow manager; no household network."""
from ipaddress import ip_address
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "simple_touch"
IDENTITY = "001122334455"


def info(identity=IDENTITY, host="192.0.2.10"):
    address = ip_address(host)
    return ZeroconfServiceInfo(ip_address=address, ip_addresses=[address], port=80,
        hostname="simpletouch-test.local.", type="_simpletouch._tcp.local.",
        name="simpletouch-test._simpletouch._tcp.local.", properties={"id": identity})


@pytest.mark.asyncio
async def test_discovered_bridge_needs_only_key(hass, enable_custom_integrations):
    result = await hass.config_entries.flow.async_init(DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF}, data=info())
    assert result["step_id"] == "discovery_confirm"
    assert result["data_schema"]({"api_key": "test-only"}) == {"api_key": "test-only"}
    with patch("custom_components.simple_touch.config_flow.BridgeApi.state",
               return_value={"device_id": IDENTITY, "name": "Test bridge"}), \
         patch("custom_components.simple_touch.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "test-only"})
        await hass.async_block_till_done()
    assert result["type"] == "create_entry"
    assert result["data"] == {"host": "http://192.0.2.10:80", "api_key": "test-only"}
    assert result["result"].unique_id == IDENTITY


@pytest.mark.asyncio
async def test_existing_bridge_updates_address_without_duplicate(hass, enable_custom_integrations):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=IDENTITY,
        data={"host": "http://192.0.2.5", "api_key": "test-only"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF}, data=info())
    assert result["reason"] == "already_configured"
    assert entry.data["host"] == "http://192.0.2.10:80"


@pytest.mark.asyncio
async def test_invalid_discovery_ignored(hass, enable_custom_integrations):
    result = await hass.config_entries.flow.async_init(DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF}, data=info(""))
    assert result["reason"] == "invalid_discovery"


@pytest.mark.asyncio
async def test_wrong_device_cannot_complete_discovery(hass, enable_custom_integrations):
    result = await hass.config_entries.flow.async_init(DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF}, data=info())
    with patch("custom_components.simple_touch.config_flow.BridgeApi.state",
               return_value={"device_id": "aabbccddeeff"}):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "test-only"})
    assert result["errors"] == {"base": "wrong_bridge"}


@pytest.mark.asyncio
async def test_bad_key_can_be_corrected(hass, enable_custom_integrations):
    from custom_components.simple_touch.api import BridgeAuthError
    result = await hass.config_entries.flow.async_init(DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF}, data=info())
    with patch("custom_components.simple_touch.config_flow.BridgeApi.state", side_effect=BridgeAuthError):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "wrong"})
    assert result["step_id"] == "discovery_confirm"
    assert result["errors"] == {"base": "invalid_auth"}
