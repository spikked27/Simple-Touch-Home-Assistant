"""Public release metadata and verified downloads; no bridge credentials here."""
import hashlib
import re

import aiohttp

from .api import BridgeError

UPDATE_BASE = "https://spikked27.github.io/Simple-Touch-Home-Assistant/"
MAX_IMAGE = 3342336


def validate_release(data):
    if (not isinstance(data, dict) or data.get("schema") != 1
            or data.get("board") != "seeed-xiao-esp32s3"
            or not isinstance(data.get("version"), str)
            or not re.fullmatch(r"\d+\.\d+\.\d+", data["version"])
            or not isinstance(data.get("sha256"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", data["sha256"])
            or type(data.get("size")) is not int or not 65536 <= data["size"] <= MAX_IMAGE
            or data.get("path") != f"firmware/{data['sha256']}.bin"):
        raise BridgeError("Incompatible firmware update package")
    return data


async def latest_release(session):
    try:
        async with session.get(UPDATE_BASE + "updates.json", allow_redirects=False,
                               timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status != 200:
                raise BridgeError("Could not check firmware updates")
            return validate_release(await response.json())
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise BridgeError("Could not check firmware updates") from err


async def download_release(session, release):
    release = validate_release(release)
    try:
        async with session.get(UPDATE_BASE + release["path"], allow_redirects=False,
                               timeout=aiohttp.ClientTimeout(total=90)) as response:
            if response.status != 200:
                raise BridgeError("Could not download firmware")
            image = bytearray()
            async for chunk in response.content.iter_chunked(16384):
                image.extend(chunk)
                if len(image) > release["size"]:
                    raise BridgeError("Firmware size mismatch")
    except (aiohttp.ClientError, TimeoutError) as err:
        raise BridgeError("Could not download firmware") from err
    if (len(image) != release["size"] or image[0] != 0xe9
            or hashlib.sha256(image).hexdigest() != release["sha256"]):
        raise BridgeError("Firmware checksum or size mismatch")
    return bytes(image)
