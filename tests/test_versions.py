"""A release must advertise the same version across both install paths."""
import json
import re
import unittest
from pathlib import Path


class ReleaseVersionTests(unittest.TestCase):
    def test_firmware_installer_and_integration_match(self):
        root = Path(__file__).resolve().parents[1]
        version = re.search(r'VERSION\[\]="([0-9.]+)"',
                            (root / "firmware/simple_touch/simple_touch.ino").read_text())[1]
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        for path in ("site/manifest.json", "custom_components/simple_touch/manifest.json"):
            self.assertEqual(json.loads((root / path).read_text())["version"], version)
