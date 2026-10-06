# Simple Touch

Local Home Assistant control for Simple Touch motorized shades, using an ESP32 and CC1101.

[![Install firmware](https://img.shields.io/badge/Install_firmware-Open_browser_installer-285d49?style=for-the-badge)](https://spikked27.github.io/Simple-Touch-Home-Assistant/)

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

There is **no motor position feedback**. Open and Close start an assumed travel window (60 seconds by default). Stop during that window assumes partially open; once it expires, the endpoint is assumed reached and later Stop presses preserve it. Adjust full travel time per shade in Shade settings. Favorite has an unknown position. After bridge restart, position starts unknown. There is no percentage slider. The bridge can listen for linked physical remotes between its own transmissions; physical-remote reception and bridge state updates have been verified on the tested hardware. Missed RF commands, power loss and obstructions can make assumed states inaccurate. Speed, limit adjustment and motor-reset commands are not exposed.

To link a physical remote, choose **Link physical remote** directly on its shade card, and briefly tap **STOP** on the existing remote. Confirm the detected remote. This only records a mapping in the bridge; it does not change motor pairing. Use the same channel you normally use for that shade. Up to eight physical remote/channel links can be stored per shade.

## Hardware

### Recognize the tested remote

The verified remote has **Simple Touch** branding, three diamond-shaped Up / Stop / Down buttons, and two **P2** buttons inside the battery compartment. These photos show the actual remote used for testing.

| Front | Battery compartment and P2 buttons |
| --- | --- |
| <img src="docs/images/simple-touch-remote-front.jpg" alt="White Simple Touch remote with three diamond-shaped buttons" width="260"> | <img src="docs/images/simple-touch-remote-p2.jpg" alt="Back of Simple Touch remote showing two P2 buttons above the batteries" width="260"> |

Matching appearance is a useful first check, not proof of RF compatibility. This identifies the tested Simple Touch-branded remote; the original equipment manufacturer is not established by the branding alone. Avoid testing P2 casually: the programming sequence can add or remove a paired remote.

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

Open the [Simple Touch installer](https://spikked27.github.io/Simple-Touch-Home-Assistant/) in desktop Chrome or Edge. You do not need to download this repository, install Arduino tools, or run a web server.

Connect the XIAO using a USB data cable. Close other serial monitors, choose Install, and select its serial port in Chrome or Edge. After flashing, use the installer's Wi-Fi setup to select a 2.4 GHz network. **Visit device** opens the bridge with your session already authorized.

If provisioning fails, open the serial console and send `SETUP`. Join the printed `SimpleTouch-…` Wi-Fi network with the printed password, then open `http://192.168.4.1`. Enter your network in Settings → Wi-Fi. The hotspot closes two minutes after Wi-Fi connects. `INFO` on USB prints the local address and bridge key. Keep the key private.

No shade pairing or movement occurs on boot, firmware installation, or Wi-Fi setup.

**Updating an existing bridge:** from v0.3.0 onward, the bridge page checks for updates when opened and every 30 minutes while open. Click **Update now** on the notification or in **Bridge settings → Firmware updates**. The page downloads the tested release, shows upload progress, and reloads after confirming the restart. Shades, physical links and Wi-Fi settings are retained. Update checks need internet access from your browser; shade control stays local.

**First upgrade from v0.1/v0.2, or manual fallback:** download the [application update](https://spikked27.github.io/Simple-Touch-Home-Assistant/simple-touch-esp32s3-update.bin), then select it under **Bridge settings → Firmware update**. This preserves your Wi-Fi, paired shades and linked remotes. Export a backup first. Do not erase user data or repeat pairing when updating.

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
3. Open **Settings → Devices & services** and select the discovered **Simple Touch** bridge.
4. Paste its key from **Bridge settings → Home Assistant**. Its address is filled in automatically.

Discovery needs local mDNS connectivity between Home Assistant and the bridge. If your network blocks discovery, use **Add integration → Simple Touch** and enter the local address manually.

The bridge also provides a **Firmware** update entity in Home Assistant. It checks hourly and lets you install firmware from Home Assistant’s Updates screen, even when the bridge webpage is closed. HACS separately handles updates to the Simple Touch integration. These are update-available indicators; phone push notifications require a Home Assistant notification automation.

Paired shades appear as cover entities. Newly paired shades are discovered within five seconds; commands are sent immediately rather than waiting for that inventory poll. The integration's Configure page and each shade's device page link back to the bridge interface.

Home Assistant must be able to reach the ESP32 on your LAN. Keep the bridge on a trusted network; its bearer-authenticated HTTP API is not intended for direct Internet exposure. Use Home Assistant's own remote access for away-from-home control.

## Performance and reliability

The RF sequence itself takes roughly 0.2–0.45 seconds. The bridge generates it locally and begins transmission without a host-side waveform upload. One radio serializes commands; a second request can wait for the current RF sequence to finish. The UI reports measured transmission duration. Measured local API round trips, including RF transmission completion, were about 0.49–0.52 seconds for Open/Close, 0.39–0.41 seconds for Stop, and 0.27 seconds for Favorite. These are not measurements of motor response time; Home Assistant end-to-end testing is still pending.

Counters are reserved in blocks in NVS before transmission. A restart skips unused values rather than reusing them. At counter exhaustion, commands fail explicitly; they do not silently wrap. The tested motor accepted commands after a restart and counter skip. A backup must not be used on two active bridges with the same remote identities.

## Protocol and attribution

Research benefited from [abrasive's blindding](https://codeberg.org/abrasive/blindding), which documents the Dooya-family packet structure and modified XXTEA, and from [Nick Whyte's Raex write-up](https://nickwhyte.com/post/2017/reversing-433mhz-raex-motorised-rf-blinds/) and [ESPSomfy-RTS](https://github.com/rstrouse/ESPSomfy-RTS). This project's implementation was checked against independently captured Simple Touch packets; the Raex and Somfy wire formats are different.

External dependencies retain their own licenses: Arduino ESP32, ArduinoJson (MIT), and Improv WiFi Library (MIT). They are fetched during builds, not relicensed here. This community project is not affiliated with the shade manufacturer, Home Assistant, or ESPHome.

[Protocol notes](docs/protocol.md) · [Development](docs/development.md) · [Testing status](docs/testing.md)
