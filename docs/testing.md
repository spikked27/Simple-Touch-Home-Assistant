# Testing status

Version 0.4.0 prepares the v1.0 release. Keep these evidence levels separate.

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
- Observed local HTTP round trips were about 0.49â€“0.52 seconds for Open/Close, 0.39â€“0.41 seconds for Stop, and 0.27 seconds for Favorite. These include transmission completion, not a measurement of when the motor begins moving.
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

## Reception and display regression (0.4.0)

- Reproduced on v0.3.0: physical Down/Stop and Up/Stop updated bridge state promptly, while the user observed a delayed webpage. Five-second UI polling could hide the intermediate movement state.
- Installed the receiver-task and one-second-refresh build through authenticated OTA. Both configured shades, all three physical-remote mappings, and travel settings survived unchanged.
- The user confirmed the webpage was much faster after refreshing it.
- A logged run decoded 44 packets and applied 10 mapped commands, with zero invalid packets, FIFO overflows, or receive-queue drops. Maximum capture-to-dispatch delay was 6 ms in that run. This is not an RF-range or motor-latency guarantee.
- Protocol and motion tests cover packet validation, Stop before/after timeout, repeat commands, reversal and clock rollover. A real Home Assistant test harness checks that a received Stop changes Closing to Open with `assumed_position: partial` on the next short poll.

## Transmission regression

- Webpage Open/Stop, Close/Stop and Favorite were retested after the receiver change; the user confirmed all controls worked.

## Remaining release checks

- Install the updated integration in the user's Home Assistant and verify physical-remote state changes there.
- Longer range/interference testing and compatibility with additional shade models remain community validation work.

No position feedback or universal Dooya compatibility is claimed. Mock tests, builds and user-observed motor tests are recorded separately.
