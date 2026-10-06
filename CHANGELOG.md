# Changelog

## 1.1.0

- Favorite action for shade covers in Home Assistant automations, without percentage controls.
- Automatic webpage connection on the bridge local network.
- Requires Home Assistant 2025.10 or newer.

## Unreleased — preparing v1.0

- Separate CC1101 reception from web requests, with a bounded receive queue and shared SPI lock.
- Apply the CC1101 stable-status-read workaround and expose reception diagnostics.
- Refresh physical-remote state every second in the webpage and Home Assistant, instead of every five seconds.
- Prevent overlapping webpage refreshes and avoid redrawing unchanged shade controls.
- Add light/dark, high-resolution brand artwork and a shorter new-user README.
- Enable HACS brand validation and document the upstream HACS icon-display limitation.

## 0.3.0

- One-click firmware updates in the bridge interface and a Home Assistant firmware update entity.
- SHA-256 and size verification for application updates.
- GitHub link in Bridge settings.

## 0.2.0

- Configurable assumed travel window, defaulting to 60 seconds.
- Stop during travel assumes partial; Stop after travel preserves the endpoint.
- Home Assistant discovery and visible physical-remote linking on shade cards.

## 0.1.0

- Browser installation and Wi-Fi provisioning for XIAO ESP32-S3 + CC1101.
- Virtual remotes, guided pairing, Open/Close/Stop/Favorite, physical-remote linking, and backups.
- Local Home Assistant integration distributed through HACS.
