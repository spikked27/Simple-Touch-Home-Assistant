# Testing status

Version 0.1.0 is experimental. Keep these evidence levels separate.

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
- Web interface add/pair/confirm and ordinary controls exercised against an isolated fixture.
- Favorite button and STOP-based physical-remote linking exercised against an isolated fixture.
- HTTP client tests cover authentication, malformed inventory, no credential redirects, no automatic command retries, and transmission acknowledgements.
- GitHub Actions checks protocol vectors, firmware compilation and integration metadata.

## Still requires live validation

- Standalone firmware RF timing and latency on the physical bridge.
- Wi-Fi provisioning and OTA update on the board.
- Home Assistant entity setup, automatic discovery of newly paired shades, unavailable/recovery behavior and reboot persistence.
- Counter reservation jumps across reboot on the motor.
- Multiple shades, range and coexistence with physical remotes.
- Physical-remote mapping and Home Assistant state updates end to end.

No position feedback or universal Dooya compatibility is claimed. Do not present a successful mock test or compile as a physical-device test.
