# Testing status

Version 0.3.0 is experimental. Keep these evidence levels separate.

## Verified on a physical shade with the radio-lab firmware

- 48 distinct captured packets from three physical remotes decrypt and re-encode exactly.
- An independent virtual identity produced three exact, CRC-valid P2 copies observed by RTL-SDR.
- Pairing produced the manual's two-jog acknowledgement.
- Generated Up followed by Stop, and Down followed by Stop, moved and stopped the shade as observed by the user.
- Generated Favorite recalled the saved position, as observed by the user.

## New standalone implementation

- XIAO ESP32-S3 firmware compiles against Arduino ESP32 3.3.8.
- Firmware flashed and booted on the XIAO ESP32-S3 with DIO flash mode. USB encoder/decoder self-test passes.
- CC1101 received and decoded all three packets from one physical Remote 1 STOP press.
- Browser-based Improv Wi-Fi provisioning completed on the board.
- User completed a fresh installation from the public HTTPS installer, Wi-Fi setup, guided shade pairing, and linking two physical remotes on v0.1.0; reported all working.
- The standalone bridge's Wi-Fi API controlled Open/Stop, Close/Stop, and Favorite, with user-observed motor movement.
- Physical Remote 1 was linked using STOP; subsequent received commands updated the bridge state with `physical_remote` as the source.
- The virtual identity, physical remote link, and radio calibration survived restart. Commands remained accepted after the counter jumped to its reserved value.
- Observed local HTTP round trips were about 0.49–0.52 seconds for Open/Close, 0.39–0.41 seconds for Stop, and 0.27 seconds for Favorite. These include transmission completion, not a measurement of when the motor begins moving.
- Web interface add/pair/confirm and ordinary controls exercised against an isolated fixture.
- Favorite button and STOP-based physical-remote linking exercised against an isolated fixture.
- HTTP client tests cover authentication, malformed inventory, no credential redirects, no automatic command retries, and transmission acknowledgements.
- GitHub Actions checks protocol vectors, firmware compilation and integration metadata.

## Version 0.2.0 changes

- Per-shade assumed travel window defaults to 60 seconds. Stop before expiry assumes partial; Stop after expiry preserves the endpoint. Favorite and restart do not invent a known position.
- Physical-remote linking is visible on each shade card.
- Home Assistant mDNS discovery pre-fills the bridge address and prompts only for its key.
- Automated tests cover timer boundaries, repeats, reversals, clock rollover, and Home Assistant discovery flows.

## Version 0.3.0 changes

- GitHub project link and firmware updates in Bridge settings.
- Automatic browser update checks and one-click download/upload/restart flow.
- Home Assistant firmware Update entity with hourly checks and installation; HACS manages integration updates separately.
- Release metadata pins the board, image size and SHA-256; the ESP32 verifies the digest before activating firmware.
- Automated tests cover release validation, version ordering, credential isolation, malformed downloads and generated package metadata.

## Still requires live validation

- OTA update through the bridge web interface.
- Version 0.2.0 timing behavior and mDNS discovery on a live Home Assistant installation.
- Home Assistant entity setup, automatic discovery of newly paired shades, unavailable/recovery behavior and reboot persistence.
- Multiple shades, range and coexistence with physical remotes.
- Physical-remote mapping and Home Assistant state updates end to end.

No position feedback or universal Dooya compatibility is claimed. Do not present a successful mock test or compile as a physical-device test.
