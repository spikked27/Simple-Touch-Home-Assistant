"""Exercise diagnostics and a verified, single-request restart in real HA."""
from unittest.mock import AsyncMock, patch
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

STATE = dict(api_version=1, device_id="001122334455", version="1.2.0", remotes=[],
             radio_ready=True, wifi_rssi=-61, ip="192.0.2.10", uptime_s=125,
             reset_reason="Power on", update_state="idle", restart_pending=False)


@pytest.mark.asyncio
async def test_diagnostics_and_restart(hass, enable_custom_integrations):
    from custom_components.simple_touch.api import BridgeError, BridgeRestartUncertain
    entry = MockConfigEntry(domain="simple_touch", unique_id=STATE["device_id"],
                            data={"host": "http://192.0.2.10", "api_key": "test-only"})
    entry.add_to_hass(hass)
    with patch('custom_components.simple_touch.api.BridgeApi.state', return_value=STATE), \
         patch('custom_components.simple_touch.update.latest_release', side_effect=BridgeError), \
         patch('custom_components.simple_touch.api.BridgeApi.status', side_effect=[
             dict(version='1.2.0', boot_id='before'), dict(version='1.2.0', boot_id='after')]), \
         patch('custom_components.simple_touch.api.BridgeApi.restart', side_effect=BridgeRestartUncertain) as restart:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get('sensor.simple_touch_bridge_wi_fi_signal').state == '-61'
        assert hass.states.get('sensor.simple_touch_bridge_wi_fi_signal').attributes['unit_of_measurement'] == 'dBm'
        assert hass.states.get('sensor.simple_touch_bridge_ip_address').state == '192.0.2.10'
        assert hass.states.get('sensor.simple_touch_bridge_uptime').state == '2'
        assert hass.states.get('binary_sensor.simple_touch_bridge_radio_problem').state == 'off'
        await hass.services.async_call('button', 'press', {'entity_id': 'button.simple_touch_bridge_restart'}, blocking=True)
        restart.assert_awaited_once()
        coordinator = hass.data['simple_touch'][entry.entry_id]
        assert not coordinator.maintenance
        coordinator.async_set_updated_data(dict(STATE, radio_ready=False))
        assert hass.states.get('binary_sensor.simple_touch_bridge_radio_problem').state == 'on'
        await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_restart_confirmation_requires_new_boot_and_expected_version():
    from custom_components.simple_touch.api import BridgeError
    from custom_components.simple_touch.maintenance import wait_for_restart
    api = AsyncMock()
    api.status.side_effect = [
        BridgeError('offline'), dict(boot_id='old', version='1.2.0'),
        dict(boot_id='new', version='1.1.0'), dict(boot_id='new', version='1.2.0')]
    result = await wait_for_restart(api, dict(boot_id='old'), '1.2.0', poll_interval=0)
    assert result['version'] == '1.2.0'
    assert api.status.await_count == 4
    api.restart.assert_not_called()
    api.upload_firmware.assert_not_called()


@pytest.mark.asyncio
async def test_failed_upload_is_reported_without_resending():
    from custom_components.simple_touch.api import BridgeError
    from custom_components.simple_touch.maintenance import wait_for_restart
    api = AsyncMock()
    api.status.return_value = dict(boot_id='old', version='1.1.0', update_state='failed', update_error='Upload interrupted')
    with pytest.raises(BridgeError, match='Upload interrupted'):
        await wait_for_restart(api, dict(boot_id='old'), '1.2.0', poll_interval=0)
    api.upload_firmware.assert_not_called()
