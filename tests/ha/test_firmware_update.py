"""Firmware updates appear and install through the real HA Update platform."""
from unittest.mock import patch
import hashlib

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

STATE = dict(api_version=1, device_id="001122334455", version="0.2.0", name="Test bridge",
             remotes=[], radio_ready=True)
IMAGE = b'\xe9' + bytes(65535)
SHA = hashlib.sha256(IMAGE).hexdigest()
RELEASE = dict(schema=1,version="0.3.0",board="seeed-xiao-esp32s3",size=len(IMAGE),
               sha256=SHA,path=f"firmware/{SHA}.bin")


@pytest.mark.asyncio
async def test_update_entity_and_install(hass, enable_custom_integrations):
    entry = MockConfigEntry(domain="simple_touch",unique_id=STATE['device_id'],
                            data={"host":"http://192.0.2.10","api_key":"test-only"})
    entry.add_to_hass(hass)
    with patch('custom_components.simple_touch.api.BridgeApi.state', return_value=STATE) as state, \
         patch('custom_components.simple_touch.update.latest_release',return_value=RELEASE), \
         patch('custom_components.simple_touch.update.download_release',return_value=IMAGE), \
         patch('custom_components.simple_touch.api.BridgeApi.status', side_effect=[
             dict(version='0.2.0', boot_id='before'), dict(version='0.3.0', boot_id='after')]), \
         patch('custom_components.simple_touch.api.BridgeApi.upload_firmware') as upload:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entities=hass.states.async_all('update')
        assert len(entities)==1
        entity=entities[0]
        assert entity.state=='on'
        assert entity.attributes['installed_version']=='0.2.0'
        assert entity.attributes['latest_version']=='0.3.0'
        state.return_value=dict(STATE,version='0.3.0')
        await hass.services.async_call('update','install',{'entity_id':entity.entity_id},blocking=True)
        await hass.async_block_till_done()
        upload.assert_awaited_once_with(IMAGE,SHA)
        assert hass.states.get(entity.entity_id).state=='off'
        await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_internet_failure_does_not_block_bridge_setup(hass, enable_custom_integrations):
    from custom_components.simple_touch.api import BridgeError
    entry=MockConfigEntry(domain='simple_touch',unique_id=STATE['device_id'],
                          data={'host':'http://192.0.2.10','api_key':'test-only'})
    entry.add_to_hass(hass)
    with patch('custom_components.simple_touch.api.BridgeApi.state',return_value=STATE), \
         patch('custom_components.simple_touch.update.latest_release',side_effect=BridgeError):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.async_all('update')[0].state=='unavailable'
        await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_checksum_mismatch_never_reaches_bridge():
    from custom_components.simple_touch.firmware import download_release
    from custom_components.simple_touch.api import BridgeError
    class Content:
        async def iter_chunked(self,size):
            yield IMAGE[:-1]+b'\x01'
    class Response:
        status=200
        content=Content()
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
    class Session:
        def get(self,url,**kwargs):
            assert url.startswith('https://spikked27.github.io/')
            assert 'headers' not in kwargs
            assert kwargs['allow_redirects'] is False
            return Response()
    with pytest.raises(BridgeError,match='checksum'):
        await download_release(Session(),RELEASE)
