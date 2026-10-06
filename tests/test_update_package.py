import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('package_update', Path(__file__).parents[1]/'scripts/package_update.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PackageTests(unittest.TestCase):
    def test_metadata_matches_exact_application_image(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'firmware/simple_touch').mkdir(parents=True)
            (root/'build').mkdir()
            (root/'firmware/simple_touch/simple_touch.ino').write_text('constexpr char VERSION[]="0.3.0";')
            data=b'\xe9'+bytes(65535)
            (root/'build/simple_touch.ino.bin').write_bytes(data)
            m=module.package(root)
            self.assertEqual(m['sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(m['size'],len(data))
            self.assertEqual((root/'site'/m['path']).read_bytes(),data)
            self.assertEqual(json.loads((root/'site/updates.json').read_text()),m)
            (root/'build/simple_touch.ino.bin').write_bytes(b'invalid')
            with self.assertRaises(ValueError): module.package(root)
