"""Exercise the actual HTTP client against an isolated aiohttp bridge."""
import importlib.util
from pathlib import Path
import unittest
from aiohttp import web, ClientSession

spec=importlib.util.spec_from_file_location('bridge_api',Path(__file__).parents[1]/'custom_components/simple_touch/api.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)

class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls=[];self.status=200;self.data={'api_version':1,'device_id':'test','remotes':[]}
        async def handler(request):
            self.calls.append((request.method,request.path,request.headers.get('Authorization')))
            if self.status==302:return web.Response(status=302,headers={'Location':'http://127.0.0.1:1/leak'})
            return web.json_response(self.data,status=self.status)
        app=web.Application();app.router.add_route('*','/{path:.*}',handler)
        self.runner=web.AppRunner(app);await self.runner.setup()
        site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start()
        port=site._server.sockets[0].getsockname()[1]
        self.session=ClientSession();self.client=api.BridgeApi(self.session,f'127.0.0.1:{port}','test-key')
    async def asyncTearDown(self):
        await self.session.close();await self.runner.cleanup()
    async def test_inventory_and_auth_header(self):
        self.assertEqual((await self.client.state())['device_id'],'test')
        self.assertEqual(self.calls,[('GET','/api/state','Bearer test-key')])
    async def test_auth_failure(self):
        self.status=401
        with self.assertRaises(api.BridgeAuthError):await self.client.state()
    async def test_no_retry_on_failed_command(self):
        self.status=503
        with self.assertRaises(api.BridgeError):await self.client.command('12345600','up')
        self.assertEqual(len(self.calls),1)
    async def test_no_credential_redirect(self):
        self.status=302
        with self.assertRaises(api.BridgeError):await self.client.state()
        self.assertEqual(len(self.calls),1)
    async def test_malformed_inventory(self):
        self.data['remotes']=[{'id':'../../secret','name':'bad'}]
        with self.assertRaises(api.BridgeError):await self.client.state()
    async def test_command_requires_ack(self):
        with self.assertRaises(api.BridgeError):await self.client.command('12345600','stop')
        self.data={'sent':True,'duration_ms':224}
        self.assertTrue((await self.client.command('12345600','stop'))['sent'])
    async def test_rejects_unknown_action_without_network(self):
        with self.assertRaises(ValueError):await self.client.command('12345600','p2')
        self.assertEqual(self.calls,[])
    def test_host_validation(self):
        self.assertEqual(api.normalize_host('simpletouch.local/'),'http://simpletouch.local')
        for host in ['http://user:pass@host','http://host/path','http://host?key=x','ftp://host','http://host:bad']:
            with self.assertRaises(ValueError):api.normalize_host(host)

if __name__=='__main__':unittest.main()
