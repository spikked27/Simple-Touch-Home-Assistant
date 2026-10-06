"""Verify lifecycle operations without resending a potentially accepted request."""
import asyncio
import time
from .api import BridgeError


async def wait_for_restart(api, before, expected_version=None, timeout=120, poll_interval=2):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        await asyncio.sleep(poll_interval)
        try:
            last = await api.status()
        except BridgeError:
            continue
        if (last.get("boot_id") and last["boot_id"] != before.get("boot_id")
                and (expected_version is None or last.get("version") == expected_version)):
            return last
        if last.get("update_state") == "failed":
            raise BridgeError(last.get("update_error") or "Firmware upload failed")
    version = last.get("version", "unknown") if last else "unreachable"
    raise BridgeError(f"Restart not confirmed. Installed firmware: {version}. Check bridge power and Wi-Fi before retrying.")
