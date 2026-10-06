<p align="center"><img src="custom_components/simple_touch/brand/icon@2x.png" alt="Simple Touch shade icon" width="100"></p>
<h1 align="center">Simple Touch</h1>
<p align="center">Your shades. Your home. Local control.</p>
<p align="center">
  <a href="https://spikked27.github.io/Simple-Touch-Home-Assistant/"><img alt="Install firmware" src="https://img.shields.io/badge/Install_firmware-Open_browser_installer-285d49?style=for-the-badge"></a>
</p>
<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=spikked27&repository=Simple-Touch-Home-Assistant&category=integration"><img alt="Add to HACS" src="https://my.home-assistant.io/badges/hacs_repository.svg"></a>
  <a href="https://github.com/spikked27/Simple-Touch-Home-Assistant/actions/workflows/checks.yml"><img alt="Checks" src="https://github.com/spikked27/Simple-Touch-Home-Assistant/actions/workflows/checks.yml/badge.svg"></a>
</p>

Add Home Assistant control to compatible Simple Touch motorized shades with a small ESP32 + CC1101 bridge. Create virtual remotes, pair shades, and link your existing remotes in a guided web interface. No cloud account, MQTT broker, or configuration files.

**Preparing for v1.0.** Core shade control has been tested on real hardware. Physical-remote responsiveness is undergoing regression testing; see [testing status](docs/testing.md) for verified behavior and remaining checks.

## What you get

- **Open, Close, Stop, and Favorite** in Home Assistant and the bridge webpage.
- **Guided setup:** create and name a shade, then follow the pairing prompts.
- **Your existing remotes still work.** Link them so the bridge can track their commands.
- **Up to 32 shades per bridge**, with up to eight physical remote/channel links per shade.
- **Automatic Home Assistant discovery**, local control, and firmware updates from either interface.
- **Backups and persistent settings.** Updates keep your shade identities, remote links, and Wi-Fi configuration.

## Get started

1. **Build the bridge.** Use a Seeed XIAO ESP32-S3, a 433 MHz CC1101 module, both antennas, and a USB data cable. Follow the [wiring guide](docs/getting-started.md#hardware).
2. **Install in your browser.** Open the [installer](https://spikked27.github.io/Simple-Touch-Home-Assistant/) in desktop Chrome or Edge. Connect by USB, install, and choose your 2.4 GHz Wi-Fi network.
3. **Add your shades.** Select **Visit device**, then **Add shade**. The bridge guides you through pairing. Select **Link physical remote** on each shade card to track your existing remotes.
4. **Connect Home Assistant.** Use **Add to HACS** above, download Simple Touch, and restart Home Assistant. Select the discovered bridge in **Settings → Devices & services** and enter the key shown in **Bridge settings → Home Assistant**.

HACS installs the Home Assistant integration; the browser installer installs the ESP32 firmware. You only set up each part once. [Full installation guide →](docs/getting-started.md)

## Is my shade compatible?

The tested remote has **Simple Touch** branding, three diamond-shaped buttons, and **P2** buttons inside the battery compartment.

<p align="center">
  <img src="docs/images/simple-touch-remote-front.jpg" alt="Tested Simple Touch remote, front" width="200">
  <img src="docs/images/simple-touch-remote-p2.jpg" alt="Tested remote battery compartment and P2 buttons" width="200">
</p>

Matching appearance is a first check, not a compatibility guarantee. Other Dooya-family shades, Somfy, and Raex are not claimed compatible. The supported firmware target is **XIAO ESP32-S3**; ESP32-C6 is not supported by this build.

## How position works

These shades do not report their position. Open and Close start a **60-second assumed travel window**, adjustable per shade. Stop during that window immediately marks the shade **partially open**. Stop after the window preserves the assumed endpoint. Favorite and bridge restart do not invent a percentage.

The bridge page and Home Assistant refresh state once per second. RF commands are sent immediately. The radio listens between its own transmissions; missed RF commands can make assumed state inaccurate. There is no percentage slider. Home Assistant's standard cover state calls any known non-closed position “open”; the `assumed_position` attribute distinguishes partial from fully open.

## Updates and help

Choose **Update now** in the bridge webpage or use its firmware update entity in Home Assistant. HACS handles integration updates separately. Export a backup before replacing a bridge; **do not erase user data or repeat pairing for routine updates**.

[Setup & wiring](docs/getting-started.md) · [Troubleshooting](docs/troubleshooting.md) · [Testing status](docs/testing.md) · [Changelog](CHANGELOG.md) · [Report a problem](https://github.com/spikked27/Simple-Touch-Home-Assistant/issues)

<details>
<summary>Development, protocol, and acknowledgements</summary>

[Development guide](docs/development.md) · [Protocol notes](docs/protocol.md) · [MIT license](LICENSE)

Research benefited from [abrasive’s blindding](https://codeberg.org/abrasive/blindding), [Nick Whyte’s Raex write-up](https://nickwhyte.com/post/2017/reversing-433mhz-raex-motorised-rf-blinds/), and [ESPSomfy-RTS](https://github.com/rstrouse/ESPSomfy-RTS). The Simple Touch packet implementation was checked against independent captures; Raex and Somfy use different wire formats.

Arduino ESP32, ArduinoJson, and Improv WiFi retain their own licenses. This is a community project, unaffiliated with the shade manufacturer, Home Assistant, or ESPHome.

</details>
