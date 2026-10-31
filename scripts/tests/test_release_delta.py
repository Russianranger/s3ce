"""Exercise transport reconstruction after edits inside a large stored member."""
import importlib.util
import json
from pathlib import Path
import random
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_delta', ROOT / 'pack_release_delta.py')
delta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delta)


class DeltaTest(unittest.TestCase):
    def reconstruct(self, old, new):
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            base, candidate, stage = work / 'base.apk', work / 'new.apk', work / 'stage'
            for path, data in ((base, old), (candidate, new)):
                with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as apk:
                    apk.writestr('assets/res.dz.jpg', data)
                    apk.writestr('unchanged', b'unchanged trailer')
            manifest = delta.pack(base, candidate, stage)
            self.assertEqual(json.loads((stage / 'manifest.json').read_text()), manifest)
            literals = (stage / 'literals.bin').read_bytes()
            original = base.read_bytes()
            rebuilt = bytearray()
            for operation in manifest['operations']:
                kind, (offset, length) = next(iter(operation.items()))
                source = original if kind == 'copy' else literals
                self.assertGreaterEqual(offset, 0)
                self.assertLessEqual(offset + length, len(source))
                rebuilt += source[offset:offset + length]
            self.assertEqual(rebuilt, candidate.read_bytes())
            self.assertEqual(delta.sha(rebuilt), manifest['sha256'])
            return len(literals)

    def test_directory_edits_and_changed_stream_length(self):
        original = random.Random(19).randbytes(2 * 1024 * 1024)
        changed = bytearray(original)
        for offset in range(6000, 12000, 17): changed[offset] ^= 255
        changed[120000:128000] = b'new compressed stream' * 17
        self.assertLess(self.reconstruct(original, changed), 40000)

    def test_unrelated_member_and_length_change(self):
        self.reconstruct(bytes(131072), bytes([255]) * 170000)

    def test_repeated_regions_and_insertions(self):
        original = b'A' * 131072 + random.Random(7).randbytes(65536) + b'B' * 131072
        changed = b'header' + original[:180000] + b'inserted' + original[180000:]
        self.assertLess(self.reconstruct(original, changed), 4096)


if __name__ == '__main__': unittest.main()
