"""Local UI fixture. Has no serial or RF access."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=dict(device_id="preview",name="Simple Touch Bridge",version="0.1.0",api_version=1,
           radio_ready=True,frequency_hz=433925000,ip="192.168.1.42",wifi_connected=True,
           max_remotes=32,remotes=[dict(id="12345600",name="Living room",paired=True,last_command="stop"),
                                  dict(id="12345700",name="Bedroom",paired=True,last_command="unknown")])
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,d,status=200):
        b=json.dumps(d).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if self.path=='/':
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write((ROOT/'firmware/web/index.html').read_bytes())
        elif self.path=='/api/setup-key':self.reply(dict(key='preview-only'))
        elif self.path=='/api/state':self.reply(STATE)
        else:self.reply({'error':'Not found'},404)
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))) or '{}')
        if self.path=='/api/remotes':
            r=dict(id=f'{len(STATE["remotes"])+100:06x}00',name=body['name'],paired=False,pair_sent=False)
            STATE['remotes'].append(r);self.reply(r,201)
        elif self.path.endswith('/pair/arm'):self.reply(dict(ticket='preview-ticket'))
        elif self.path.endswith('/pair/send'):
            r=next(r for r in STATE['remotes'] if r['id']==self.path.split('/')[3]);r['pair_sent']=True;self.reply(dict(sent=True))
        elif self.path.endswith('/pair/confirm'):
            r=next(r for r in STATE['remotes'] if r['id']==self.path.split('/')[3]);r['paired']=True;r['pair_sent']=False;self.reply(STATE)
        elif self.path.endswith('/command'):
            r=next(r for r in STATE['remotes'] if r['id']==self.path.split('/')[3])
            r.update(last_command=body['action'],state_source='bridge')
            self.reply(dict(sent=True,duration_ms=224))
        elif self.path.endswith('/learn/start'):self.reply(dict(listening=True))
        elif self.path.endswith('/learn/status'):self.reply(dict(listening=True,candidate='abcdef00',groups=1))
        elif self.path.endswith('/learn/confirm'):
            r=next(r for r in STATE['remotes'] if r['id']==self.path.split('/')[3])
            r['physical']=[dict(id='abcdef00',groups=1)];self.reply(STATE)
        elif self.path.endswith('/learn/remove'):
            r=next(r for r in STATE['remotes'] if r['id']==self.path.split('/')[3])
            r['physical']=[];self.reply(STATE)
        else:self.reply(dict(error='Not implemented in preview'),404)
if __name__=='__main__':
    print('Preview: http://127.0.0.1:18888',flush=True)
    ThreadingHTTPServer(('127.0.0.1',18888),Handler).serve_forever()
