#!/usr/bin/env python3
"""Independent asset-integrity checks; run with the supplied APK or raw res.dz."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import lzma
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile
import zlib

MODULE = Path(__file__).resolve().parents[1] / "ui_indices.py"
SPEC = importlib.util.spec_from_file_location("ui_indices", MODULE)
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)
SOURCE = b""


def directory(data: bytes):
    assert data[:4] == b"DTRZ"
    count, directories = struct.unpack_from("<HH", data, 4)
    cursor = 8
    for _ in range(count + directories):
        cursor = data.index(0, cursor) + 1
    cursor += count * 6
    assert struct.unpack_from("<HH", data, cursor) == (1, count)
    table = cursor + 4
    records = [struct.unpack_from("<4I", data, table + i * 16) for i in range(count)]
    return table, records


def entry(data: bytes, row: tuple[int, int, int, int]) -> bytes:
    offset, size, duplicate, flags = row
    assert size == duplicate and flags == 0x200
    # Stop at this stream's end, independently of following entry metadata.
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    result = decoder.decompress(data[offset:])
    assert decoder.eof and len(result) == size
    return result


def m3g(data: bytes):
    assert data[:12] == b"\xabJSR184\xbb\r\n\x1a\n"
    cursor = 12
    objects = []
    section_count = 0
    while cursor < len(data):
        compression, size, uncompressed = struct.unpack_from("<BII", data, cursor)
        assert compression == 0 and size == uncompressed + 13
        end = cursor + size
        assert end <= len(data)
        assert zlib.adler32(data[cursor:end - 4]) == struct.unpack_from("<I", data, end - 4)[0]
        body = data[cursor + 9:end - 4]
        offset = 0
        while offset < len(body):
            kind, length = struct.unpack_from("<BI", body, offset)
            offset += 5
            objects.append((kind, body[offset:offset + length]))
            offset += length
        assert offset == len(body)
        cursor = end
        section_count += 1
    assert cursor == len(data) and section_count == 2
    assert struct.unpack_from("<II", objects[0][1], 3) == (len(data), len(data))
    return objects


def strip(body: bytes):
    assert body[:12] == bytes(12)
    encoding = body[12]
    if encoding == 1:
        first = body[13]
        cursor = 14
        indices = None
    elif encoding == 0x81:
        count = struct.unpack_from("<I", body, 13)[0]
        indices = list(body[17:17 + count])
        cursor = 17 + count
    else:
        raise AssertionError("unexpected strip encoding")
    count = struct.unpack_from("<I", body, cursor)[0]
    cursor += 4
    lengths = struct.unpack_from("<" + str(count) + "I", body, cursor)
    assert cursor + count * 4 == len(body)
    if indices is None:
        indices = list(range(first, first + sum(lengths)))
    return indices, lengths


class UIIndexPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = SOURCE
        cls.patched = PATCH.patched_bytes(SOURCE)
        cls.table, cls.before = directory(cls.original)
        after_table, cls.after = directory(cls.patched)
        assert after_table == cls.table

    def test_ordered_repack_preserves_all_other_compressed_payload_bytes(self):
        delta = len(self.patched) - len(self.original)
        self.assertEqual(delta, -35)
        self.assertEqual(self.original[:self.table], self.patched[:self.table])
        end_table = self.table + len(self.before) * 16
        first_payload = self.before[0][0]
        self.assertEqual(self.original[end_table:first_payload], self.patched[end_table:first_payload])
        self.assertEqual(self.after[104], (1593019, 141639, 141639, 0x200))
        for i, (before, after) in enumerate(zip(self.before, self.after)):
            if i == 104:
                continue
            expected = (before[0] + (delta if i > 104 else 0), *before[1:])
            self.assertEqual(after, expected, "directory entry " + str(i))
            old_end = self.before[i + 1][0] if i + 1 < len(self.before) else len(self.original)
            new_end = self.after[i + 1][0] if i + 1 < len(self.after) else len(self.patched)
            self.assertEqual(self.original[before[0]:old_end], self.patched[after[0]:new_end],
                             "compressed payload " + str(i))
        self.assertTrue(all(a[0] < b[0] for a, b in zip(self.after, self.after[1:])))
        self.assertEqual(hashlib.sha256(self.patched).hexdigest(), PATCH.PATCHED_SHA256)

    def test_all_677_nontarget_entries_decode_identically(self):
        for i, (before, after) in enumerate(zip(self.before, self.after)):
            if i != 104:
                with self.subTest(entry=i):
                    self.assertEqual(entry(self.original, before), entry(self.patched, after))

    def test_all_objects_preserved_except_equivalent_strip_and_header_sizes(self):
        raw_before = entry(self.original, self.before[104])
        raw_after = entry(self.patched, self.after[104])
        before, after = m3g(raw_before), m3g(raw_after)
        self.assertEqual(len(before), 2500)
        self.assertEqual(len(after), len(before))
        self.assertEqual(hashlib.sha256(raw_after).hexdigest(), PATCH.PATCHED_M3G_SHA256)
        for i, (a, b) in enumerate(zip(before, after)):
            self.assertEqual(a[0], b[0])
            if i == 0:
                self.assertEqual(a[1][:3] + a[1][11:], b[1][:3] + b[1][11:])
            elif i == 4:
                self.assertEqual(a[0], 11)
                self.assertEqual(strip(a[1]), ([0, 1, 2, 3], (4,)))
                self.assertEqual(strip(a[1]), strip(b[1]))
                self.assertEqual(len(b[1]) - len(a[1]), 7)
            else:
                self.assertEqual(a, b, "changed M3G object " + str(i + 1))
        meshes = [body for kind, body in after if kind == 14]
        self.assertEqual(len(meshes), 530)
        self.assertTrue(all(struct.unpack_from("<I", body, 70)[0] == 5 for body in meshes))

    def test_idempotence_and_file_api(self):
        self.assertEqual(PATCH.patched_bytes(self.patched), self.patched)
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            target = root / "assets/res.dz.jpg"
            target.parent.mkdir()
            target.write_bytes(self.original)
            self.assertTrue(PATCH.apply(root))
            self.assertFalse(PATCH.apply(root))
            self.assertEqual(target.read_bytes(), self.patched)

    def test_tampered_original_or_patched_archives_are_rejected(self):
        for source in (self.original, self.patched):
            for offset in (0, self.table + 104 * 16, 1593019, len(source) - 1):
                with self.subTest(length=len(source), offset=offset):
                    altered = bytearray(source)
                    altered[offset] ^= 1
                    with self.assertRaises(ValueError):
                        PATCH.patched_bytes(bytes(altered))
        raw = bytearray(entry(self.original, self.before[104]))
        raw[251] ^= 1
        with self.assertRaises(ValueError):
            PATCH.patched_m3g_bytes(bytes(raw))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    if zipfile.is_zipfile(args.source):
        with zipfile.ZipFile(args.source) as apk:
            SOURCE = apk.read("assets/res.dz.jpg")
    else:
        SOURCE = args.source.read_bytes()
    unittest.main(argv=[__file__], verbosity=2)
