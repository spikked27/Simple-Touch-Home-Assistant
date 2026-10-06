"""Publish the exact application image and its integrity metadata together."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package(root=ROOT):
    version = re.search(r'VERSION\[\]="([0-9.]+)"',
                       (root/'firmware/simple_touch/simple_touch.ino').read_text()).group(1)
    image = (root/'build/simple_touch.ino.bin').read_bytes()
    if not 65536 <= len(image) <= 3342336 or image[0] != 0xe9:
        raise ValueError('Not a supported ESP32 application image')
    digest = hashlib.sha256(image).hexdigest()
    path = f'firmware/{digest}.bin'
    target = root/'site'/path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(image)
    manifest = dict(schema=1, version=version, board='seeed-xiao-esp32s3',
                    size=len(image), sha256=digest, path=path)
    (root/'site/updates.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    print(json.dumps(package()))
