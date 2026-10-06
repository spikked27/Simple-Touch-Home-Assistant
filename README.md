# Simple Touch

Local Home Assistant control for Simple Touch motorized shades, using an ESP32 and CC1101.

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=spikked27&repository=Simple-Touch-Home-Assistant&category=integration)
[![Checks](https://github.com/spikked27/Simple-Touch-Home-Assistant/actions/workflows/checks.yml/badge.svg)](https://github.com/spikked27/Simple-Touch-Home-Assistant/actions/workflows/checks.yml)

**Early experimental release.** The RF protocol, creation of a new virtual remote, pairing, and UP/DOWN/STOP/favorite-position commands have been verified on a Simple Touch shade. The standalone firmware and Home Assistant integration are new; see [testing status](docs/testing.md) for their separate validation status. Compatibility with every Dooya-family motor is not claimed.

## What it does

- Up to 32 independent virtual remotes per bridge. Use additional bridges for range or more shades.
- Add and name shades in a responsive web interface, with step-by-step pairing.
- Native Home Assistant shade entities with Open, Close and Stop, plus a Favorite position button, usable in dashboards, scenes and automations.
- Local HTTP commands go directly to the ESP32. No MQTT broker, cloud account, computer helper, or command polling delay.
- Identities and counters persist on the ESP32. Adding a shade does not require recompiling firmware.
- Browser Wi-Fi provisioning via Improv Serial, plus an authenticated setup hotspot fallback.
- Remote backup/import and authenticated firmware updates from the bridge interface.

There is **no motor position feedback**. Open and Close set an assumed endpoint state; Stop and Favorite leave the position unknown. There is no percentage slider. The bridge can listen for linked physical remotes between its own transmissions; this listener still needs live validation. Missed RF commands, power loss and obstructions can make assumed states inaccurate. Speed, limit adjustment and motor-reset commands are not exposed.

To link a physical remote, open the shade’s settings, choose **Physical remotes → Link physical remote**, and briefly tap **STOP** on the existing remote. Confirm the detected remote. This only records a mapping in the bridge; it does not change motor pairing. Use the same channel you normally use for that shade. Up to eight physical remote/channel links can be stored per shade.

## Hardware

The initial supported board is the **Seeed XIAO ESP32-S3**, with a 433 MHz CC1101 module and suitable antenna. Use 3.3 V power and logic.

| CC1101 | XIAO ESP32-S3 |
| --- | --- |
| VCC | 3V3 |
| GND | GND |
| SCK | D8 / GPIO7 |
| MISO | D9 / GPIO8 |
| MOSI | D10 / GPIO9 |
| CSN | D5 / GPIO6 |
| GDO0 | D2 / GPIO3 |

The XIAO ESP32-S3 has no native Zigbee radio. CC1101 handles the shade's 433 MHz FSK; Wi-Fi connects the bridge to Home Assistant.

## Installation

HACS installs the **Home Assistant integration**, not ESP32 firmware. Install both parts once.

### 1. Install the bridge firmware

Use the browser installer supplied with the project at `site/index.html`, served from HTTPS or localhost. Release packaging instructions are in [development](docs/development.md). The firmware artifact is also built by GitHub Actions.

Connect the XIAO using a USB data cable. Close other serial monitors, choose Install, and select its serial port in Chrome or Edge. After flashing, use the installer's Wi-Fi setup to select a 2.4 GHz network. **Visit device** opens the bridge with your session already authorized.

If provisioning fails, open the serial console and send `SETUP`. Join the printed `SimpleTouch-…` Wi-Fi network with the printed password, then open `http://192.168.4.1`. Enter your network in Settings → Wi-Fi. The hotspot closes two minutes after Wi-Fi connects. `INFO` on USB prints the local address and bridge key. Keep the key private.

No shade pairing or movement occurs on boot, firmware installation, or Wi-Fi setup.

### 2. Add a shade

Open the bridge web interface and choose **Add shade**. Name it, then follow the pairing guide:

1. On a physical remote already paired to the target shade, press P2. Wait for one jog.
2. Press P2 again. Wait for one jog.
3. Immediately click **Two jogs — pair now**. The bridge sends its new identity's P2.
4. Confirm the shade jogged twice, then test Open, Stop and Close.

Only the intended shade should be powered during pairing. **The same sequence can remove a paired remote.** The web interface prevents casually sending the pairing packet twice. Deleting a remote from the bridge does not remove it from the motor; export a backup before deleting records you may need again.

### 3. Connect Home Assistant

1. Click **Add to HACS** above, or add this repository manually in HACS as an **Integration**.
2. Download Simple Touch and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration → Simple Touch**.
4. Enter the bridge's local address and its key from **Bridge settings → Home Assistant**.

Paired shades appear as cover entities. Newly paired shades are discovered within five seconds; commands are sent immediately rather than waiting for that inventory poll. The integration's Configure page and each shade's device page link back to the bridge interface.

Home Assistant must be able to reach the ESP32 on your LAN. Keep the bridge on a trusted network; its bearer-authenticated HTTP API is not intended for direct Internet exposure. Use Home Assistant's own remote access for away-from-home control.

## Performance and reliability

The RF sequence itself takes roughly 0.2–0.45 seconds. The bridge generates it locally and begins transmission without a host-side waveform upload. One radio serializes commands; a second request can wait for the current RF sequence to finish. The UI reports measured transmission duration. End-to-end latency still depends on Wi-Fi and the motor; no measured latency guarantee is claimed yet.

Counters are reserved in blocks in NVS before transmission. A restart skips unused values rather than reusing them. At counter exhaustion, commands fail explicitly; they do not silently wrap. This skip behavior requires live reboot validation on the target motor. A backup must not be used on two active bridges with the same remote identities.

## Protocol and attribution

Research benefited from [abrasive's blindding](https://codeberg.org/abrasive/blindding), which documents the Dooya-family packet structure and modified XXTEA, and from [Nick Whyte's Raex write-up](https://nickwhyte.com/post/2017/reversing-433mhz-raex-motorised-rf-blinds/) and [ESPSomfy-RTS](https://github.com/rstrouse/ESPSomfy-RTS). This project's implementation was checked against independently captured Simple Touch packets; the Raex and Somfy wire formats are different.

External dependencies retain their own licenses: Arduino ESP32, ArduinoJson (MIT), and Improv WiFi Library (MIT). They are fetched during builds, not relicensed here. This community project is not affiliated with the shade manufacturer, Home Assistant, or ESPHome.

[Protocol notes](docs/protocol.md) · [Development](docs/development.md) · [Testing status](docs/testing.md)
