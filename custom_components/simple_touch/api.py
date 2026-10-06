"""Local bridge API; never retry a command that might already have transmitted."""
from urllib.parse import urlsplit

import aiohttp


class BridgeError(Exception):
    """A bridge request failed."""


class BridgeAuthError(BridgeError):
    """The bridge key was rejected."""


class BridgeUpdateUncertain(BridgeError):
    """Upload connection was lost; check the version instead of retrying."""


class BridgeRestartUncertain(BridgeError):
    """Restart response was lost; verify the boot identity instead of resending."""


def normalize_host(value: str) -> str:
    value = value.strip().rstrip("/")
    if "://" not in value:
        value = "http://" + value
    parsed = urlsplit(value)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")):
        raise ValueError("Enter the bridge address without a path or credentials")
    _ = parsed.port  # Reject malformed ports.
    return value


class BridgeApi:
    def __init__(self, session: aiohttp.ClientSession, host: str, key: str):
        self.session = session
        self.host = normalize_host(host)
        self.key = key

    async def request(self, path: str, body: dict | None = None) -> dict:
        try:
            async with self.session.request(
                "POST" if body is not None else "GET", self.host + "/api/" + path,
                json=body, headers={"Authorization": "Bearer " + self.key},
                timeout=aiohttp.ClientTimeout(total=5), allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise BridgeAuthError("Bridge key rejected")
                if response.status != 200:
                    raise BridgeError(f"Bridge returned HTTP {response.status}")
                data = await response.json()
                if not isinstance(data, dict):
                    raise BridgeError("Invalid bridge response")
                return data
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise BridgeError("Cannot communicate with bridge") from err

    async def state(self) -> dict:
        data = await self.request("state")
        if (data.get("api_version") != 1 or not isinstance(data.get("device_id"), str)
                or not isinstance(data.get("remotes"), list)):
            raise BridgeError("Unsupported bridge API")
        for remote in data["remotes"]:
            if (not isinstance(remote, dict) or not isinstance(remote.get("id"), str)
                    or len(remote["id"]) != 8 or any(c not in "0123456789abcdef" for c in remote["id"])
                    or not isinstance(remote.get("name"), str)):
                raise BridgeError("Invalid remote list")
        return data

    async def status(self) -> dict:
        data = await self.request("status")
        if not data.get("boot_id") or not data.get("version"):
            raise BridgeError("Bridge did not report its boot identity")
        return data

    async def restart(self) -> None:
        try:
            async with self.session.post(self.host + "/api/restart", json={},
                headers={"Authorization": "Bearer " + self.key},
                timeout=aiohttp.ClientTimeout(total=10), allow_redirects=False) as response:
                if response.status in (401, 403):
                    raise BridgeAuthError("Bridge key rejected")
                if response.status != 200 or (await response.json()).get("restarting") is not True:
                    raise BridgeError("Bridge did not acknowledge restart")
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise BridgeRestartUncertain("Restart response lost; checking boot identity") from err

    async def command(self, remote: str, action: str) -> dict:
        if action not in ("up", "down", "stop", "favorite"):
            raise ValueError("Unsupported command")
        data = await self.request(f"remotes/{remote}/command", {"action": action})
        if data.get("sent") is not True:
            raise BridgeError("Bridge did not confirm transmission")
        return data

    async def upload_firmware(self, image: bytes, sha256: str) -> None:
        form = aiohttp.FormData()
        form.add_field("firmware", image, filename="simple-touch-update.bin",
                       content_type="application/octet-stream")
        try:
            async with self.session.post(self.host + "/api/update", data=form,
                headers={"Authorization": "Bearer " + self.key,
                         "X-Firmware-SHA256": sha256, "X-Firmware-Size": str(len(image))},
                timeout=aiohttp.ClientTimeout(total=180), allow_redirects=False) as response:
                if response.status in (401, 403):
                    raise BridgeAuthError("Bridge key rejected")
                if response.status != 200 or (await response.json()).get("restarting") is not True:
                    raise BridgeError("Bridge rejected the firmware update")
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise BridgeUpdateUncertain("Update connection interrupted; checking installed version") from err
