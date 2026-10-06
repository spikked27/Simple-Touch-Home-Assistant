# Development

## Firmware

Install Arduino CLI and the Espressif board index, then install `esp32:esp32@3.3.8`. Obtain ArduinoJson v7.4.2 and Improv WiFi Library revision `e37c244e0080349e191252acf4bce146eca118e0` in local library directories.

```sh
python scripts/embed_web.py
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,FlashMode=dio \
  --library /path/to/ArduinoJson --library /path/to/ImprovWiFi \
  --output-dir build firmware/simple_touch
```

The board profile uses its standard 8 MB flash partition scheme. Do not substitute an ESP32-C3/C6/S2 binary or pin layout. USB serial `SELFTEST` generates a known packet without transmitting RF; `INFO` prints private provisioning details; `SETUP` enables the password-protected setup hotspot.

The RF module uses the Arduino ESP32 RMT peripheral at 1 MHz with 25 microsecond symbols. HTTP handlers generate waveforms locally. RF transmissions are serialized by the firmware event loop, and all ordinary commands are explicit API requests. No automatic transmit runs on startup or reconnect.

## Installer packaging

The build produces `simple_touch.ino.merged.bin`. Copy it to `site/firmware.bin` after validating flash mode and board settings. `simple_touch.ino.bin` is the application-only image for authenticated web OTA. Keep filenames and manifest versions aligned. Never distribute a full flash dump: it can contain saved Wi-Fi credentials, bridge keys and paired identities.

The Checks workflow builds the firmware and publishes `site/` to GitHub Pages only after tests, hassfest, HACS validation, and firmware compilation pass. Repository maintainers enable this once under **Settings → Pages → Build and deployment → Source → GitHub Actions**. Pull requests never publish the installer.

End users visit the hosted installer directly. They do not download the website, run a local server, or install Arduino tools. A localhost server is only useful for developing this page. The browser-installer artifact remains available for maintainers and offline hosting.

## Home Assistant

Copy `custom_components/simple_touch` into a development Home Assistant configuration, restart, and add the integration. HACS custom-repository installation uses the same directory. The integration requires no extra pip dependencies beyond Home Assistant's aiohttp.

Tests:

```sh
pip install aiohttp
python -m unittest discover -s tests -p 'test_*.py' -v
g++ -std=c++17 tests/protocol_test.cpp -o /tmp/protocol-test
/tmp/protocol-test
python tests/mock_bridge.py
```

The UI preview at `http://127.0.0.1:18888` is isolated from hardware and cannot move a shade. CI additionally compiles firmware and validates HACS/Home Assistant metadata. Real Home Assistant integration and physical shade tests must be recorded separately from mocks.

## API version 1

All endpoints except `/`, `/api/status`, and AP-only `/api/setup-key` require `Authorization: Bearer BRIDGE_KEY`.

- `GET /api/state`: bridge health and remote inventory.
- `POST /api/remotes`: create with `name`, or import with `id`, `next_counter`, `paired`.
- `POST /api/remotes/ID/command`: `action` is `up`, `down`, `stop`, or `favorite`. Replies after the RF sequence finishes. Do not automatically retry after a timeout.
- Physical remote links: POST `learn/start` opens a 60-second listening session, `learn/status` reports a candidate STOP identity, `learn/confirm` saves it, and `learn/remove` takes an `id` to unlink. These operations never transmit RF.
- Pairing: `pair/arm` returns a 120-second one-use `ticket`; `pair/send` consumes it; `pair/confirm` requires `two_jogs: true`.
- `POST /api/remotes/ID/rename`, `DELETE /api/remotes/ID`.
- `GET /api/backup`: records with reserved next counters; no Wi-Fi credentials or bridge key.
- `POST /api/wifi`, `/api/radio`, `/api/restart`; multipart `POST /api/update` for application firmware.

Pending pairing state survives restart. A repeated send is rejected until its result is resolved. Deletion leaves a counter tombstone to prevent accidental identity reuse. Lost/reset flash requires restoring from a recent backup or pairing new identities. A backup should be taken after stopping use of the original bridge, and restored to a fresh replacement; it is not a synchronization mechanism.
