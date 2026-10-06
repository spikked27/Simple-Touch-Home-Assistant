# Troubleshooting

[← Overview](../README.md)

## Physical Stop seems delayed

Update the bridge firmware and the Home Assistant integration, then refresh the bridge webpage. Both interfaces refresh state once per second. Versions through 0.3.0 refreshed every five seconds, so a quick Open → Stop sequence could happen entirely between refreshes.

Stop during a shade's travel window changes its assumed position immediately; the window is not a delay before processing Stop. Its default is 60 seconds. After that window, Stop preserves the assumed endpoint.

If the bridge page updates but Home Assistant does not, check that the integration update is installed and Home Assistant has restarted. Home Assistant displays a partially open shade as **Open**; its `assumed_position` attribute reads `partial`.

## A physical remote is not detected

Choose **Link physical remote** on the correct shade card and briefly tap Stop on the channel you normally use. Each shade needs its own mapping, even if one physical remote operates several shades. Linking does not pair or unpair anything at the motor.

Keep the CC1101 antenna clear of metal and attach the XIAO's separate Wi-Fi antenna. Test near the bridge first. The CC1101 cannot receive while it is transmitting. Independent bridges may be needed for distant rooms.

The authenticated `/api/diagnostics` endpoint provides reception, invalid-packet, duplicate, overflow, and queue-drop counts plus recent decoded packets. This is for diagnosis; normal setup never needs it. Diagnostics include remote identities: redact addresses before posting them publicly, and never publish your bridge key or backups.

## Home Assistant does not discover the bridge

Install the integration through HACS and restart Home Assistant. mDNS discovery needs network connectivity between Home Assistant and the bridge. If discovery is blocked by VLANs or your router, use **Add integration → Simple Touch** and enter the bridge's local address and key manually.

## HACS shows a missing icon

Simple Touch bundles light/dark and high-resolution icons in the integration's `brand/` directory. Local brand images require Home Assistant 2026.3 or newer. Some HACS versions still fetch custom-integration icons from the old public image service instead of using these files; this is tracked in [HACS issue 5223](https://github.com/hacs/integration/issues/5223). Updating this integration alone cannot repair that HACS display issue.

## Updating or replacing a bridge

Use **Update now** in Bridge settings or the firmware update entity in Home Assistant. HACS updates the integration separately. Both parts must be updated to receive changes to both interfaces.

Routine updates preserve your settings. Export a remote backup before replacing hardware. Keep the old bridge powered off when restoring its identities to another bridge. Do not erase user data or repeat P2 pairing to install an update: the same P2 sequence can remove a paired remote.

## Reporting a problem

Include firmware and integration versions, board/module type, whether it affects the bridge webpage or Home Assistant, and whether ordinary bridge commands or physical remote presses are affected. Describe the sequence of buttons and approximate timing. Do not include keys, Wi-Fi passwords, or unredacted remote backups.
