const {test}=require('node:test');
const assert=require('node:assert/strict');
const updates=require('../firmware/web/updater.js');
const sha='a'.repeat(64);
const manifest={schema:1,version:'0.3.0',board:'seeed-xiao-esp32s3',size:65536,sha256:sha,path:`firmware/${sha}.bin`};
test('numeric versions reject downgrades and do not compare lexically',()=>{
 assert(updates.newer('0.10.0','0.9.9'));
 for(const v of ['0.2.9','0.3.0','garbage','0.4.0-beta'])assert(!updates.newer(v,'0.3.0'));
});
test('only matching boards and checksum-addressed relative images accepted',()=>{
 assert.deepEqual(updates.validate(manifest),manifest);
 for(const bad of [{board:'esp32c6'},{sha256:'x'.repeat(64)},{size:99999999},{size:1},{path:'https://evil.example/firmware.bin'},{path:'../firmware.bin'},{version:'latest'}])
  assert.throws(()=>updates.validate({...manifest,...bad}));
});
test('public update checks omit credentials and referrers',async()=>{
 const m=await updates.check(async(url,options)=>{
  assert.equal(url,'https://spikked27.github.io/Simple-Touch-Home-Assistant/updates.json');
  assert.equal(options.credentials,'omit');assert.equal(options.referrerPolicy,'no-referrer');assert.equal(options.headers,undefined);
  return {ok:true,json:async()=>manifest};
 });assert.equal(m.version,'0.3.0');
});
test('failed check is not reported as up to date',async()=>{
 await assert.rejects(updates.check(async()=>({ok:false})),/Could not check/);
});
test('download uses only the validated release path and no bridge key',async()=>{
 const bytes=new Uint8Array(65536);bytes[0]=0xe9;
 const blob=await updates.download(manifest,async(url,options)=>{
  assert.equal(url,`https://spikked27.github.io/Simple-Touch-Home-Assistant/firmware/${sha}.bin`);
  assert.equal(options.headers,undefined);assert.equal(options.credentials,'omit');
  return {ok:true,blob:async()=>new Blob([bytes])};
 });assert.equal(blob.size,65536);
});
test('missing, truncated and invalid images fail before any upload',async()=>{
 await assert.rejects(updates.download(manifest,async()=>({ok:false})),/not download/);
 for(const bytes of [new Uint8Array(123),new Uint8Array(65536)])
  await assert.rejects(updates.download(manifest,async()=>({ok:true,blob:async()=>new Blob([bytes])})),/incomplete or invalid/);
});
