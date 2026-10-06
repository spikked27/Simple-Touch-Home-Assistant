/* Public downloads never receive the bridge's authorization key. */
const SimpleTouchUpdates = (() => {
  const base = 'https://spikked27.github.io/Simple-Touch-Home-Assistant/';
  const board = 'seeed-xiao-esp32s3';
  function newer(candidate, current) {
    const parse = v => /^\d+\.\d+\.\d+$/.test(v) ? v.split('.').map(Number) : null;
    const a = parse(candidate), b = parse(current);
    if (!a || !b) return false;
    for (let i=0;i<3;i++) if (a[i]!==b[i]) return a[i]>b[i];
    return false;
  }
  function validate(m) {
    if (!m || m.schema!==1 || m.board!==board || !/^\d+\.\d+\.\d+$/.test(m.version)
        || !/^[a-f0-9]{64}$/.test(m.sha256) || !Number.isInteger(m.size)
        || m.size<65536 || m.size>3342336 || m.path!==`firmware/${m.sha256}.bin`)
      throw Error('The update package is not compatible with this bridge.');
    return m;
  }
  async function check(fetcher=fetch) {
    const r=await fetcher(base+'updates.json', {cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(15000)});
    if (!r.ok) throw Error('Could not check for updates. Try again later.');
    return validate(await r.json());
  }
  async function download(manifest, fetcher=fetch) {
    const m=validate(manifest);
    const r=await fetcher(base+m.path, {cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(90000)});
    if (!r.ok) throw Error('Could not download the update. Your bridge has not changed.');
    const blob=await r.blob();
    if (blob.size!==m.size || new Uint8Array(await blob.slice(0,1).arrayBuffer())[0]!==0xe9)
      throw Error('The firmware download is incomplete or invalid. Try again.');
    return blob;
  }
  return {check,download,newer,validate};
})();
if (typeof module!=='undefined') module.exports=SimpleTouchUpdates;
