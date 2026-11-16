#!/usr/bin/env python3
"""Independent DTRZ/resource integrity checks using the supplied original asset."""
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

SPEC = importlib.util.spec_from_file_location(
    'relationship_tuning', Path(__file__).resolve().parents[1] / 'relationship_tuning.py')
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)
SOURCE = b''


def directory(data):
    assert data[:4] == b'DTRZ'
    count, directories = struct.unpack_from('<HH', data, 4)
    cursor = 8
    for _ in range(count + directories):
        cursor = data.index(0, cursor) + 1
    cursor += count * 6
    assert struct.unpack_from('<HH', data, cursor) == (1, count)
    table = cursor + 4
    return table, [struct.unpack_from('<4I', data, table + 16 * i) for i in range(count)]


def resource(data, row):
    offset, size, duplicate, flags = row
    assert size == duplicate and flags == 0x200
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    raw = decoder.decompress(data[offset:])
    assert decoder.eof and len(raw) == size
    return raw


def graph(raw):
    assert raw[0x57d:0x57f] == bytes((2, 15))
    rows, cursor = [], 0x57f
    for _ in range(15):
        header = raw[cursor:cursor + 8]
        cursor += 8
        edges = []
        for _ in range(header[7]):
            edges.append(struct.unpack_from('>BBh', raw, cursor))
            cursor += 4
        rows.append((header, edges))
    return rows, cursor


class RelationshipTuningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = SOURCE
        cls.patched = PATCH.patched_bytes(SOURCE)
        cls.table, cls.before = directory(cls.original)
        table, cls.after = directory(cls.patched)
        assert table == cls.table and len(cls.before) == len(cls.after) == 678
        cls.raw_before = resource(cls.original, cls.before[6])
        cls.raw_after = resource(cls.patched, cls.after[6])

    def test_archive_tables_and_all_677_other_compressed_payloads_are_preserved(self):
        delta = len(self.patched) - len(self.original)
        self.assertEqual(self.original[:self.table], self.patched[:self.table])
        first = self.before[0][0]
        end_table = self.table + 678 * 16
        self.assertEqual(self.original[end_table:first], self.patched[end_table:first])
        self.assertEqual(self.after[6], (40464, 22038, 22038, 0x200))
        for index, (before, after) in enumerate(zip(self.before, self.after)):
            if index == 6:
                continue
            with self.subTest(entry=index):
                self.assertEqual(after, (before[0] + (delta if index > 6 else 0), *before[1:]))
                old_end = self.before[index + 1][0] if index < 677 else len(self.original)
                new_end = self.after[index + 1][0] if index < 677 else len(self.patched)
                self.assertEqual(self.original[before[0]:old_end],
                                 self.patched[after[0]:new_end])
        self.assertTrue(all(a[0] < b[0] for a, b in zip(self.after, self.after[1:])))

    def test_all_677_other_resources_decode_identically(self):
        for index, (before, after) in enumerate(zip(self.before, self.after)):
            if index != 6:
                with self.subTest(entry=index):
                    self.assertEqual(resource(self.original, before), resource(self.patched, after))

    def test_only_good_and_best_friend_receive_appended_romance_edges(self):
        before, end_before = graph(self.raw_before)
        after, end_after = graph(self.raw_after)
        self.assertEqual((end_before, end_after), (0x65f, 0x667))
        self.assertEqual(self.raw_before[:0x57f], self.raw_after[:0x57f])
        self.assertEqual(self.raw_before[end_before:], self.raw_after[end_after:])
        self.assertEqual(len(self.raw_after), len(self.raw_before) + 8)
        for state, ((old_header, old_edges), (new_header, new_edges)) in enumerate(zip(before, after)):
            with self.subTest(state=state):
                if state in (6, 7):
                    self.assertEqual(new_header[:7], old_header[:7])
                    self.assertEqual(new_header[7], old_header[7] + 1)
                    self.assertEqual(new_edges, old_edges + [(8, 1, 10)])
                else:
                    self.assertEqual((new_header, new_edges), (old_header, old_edges))
        # Preserve every original first-match condition before the new edge.
        self.assertEqual(after[6][1], [(5, 0, -10), (7, 0, 25), (8, 1, 10)])
        self.assertEqual(after[7][1], [(6, 0, -15), (8, 1, 10)])
        self.assertEqual(after[5], before[5])  # Friend's established route remains untouched.

    def test_pinned_output_and_lzma_properties(self):
        self.assertEqual(hashlib.sha256(self.patched).hexdigest(),
                         '82357d3082b520ebcc583ff2526fc6066c51d39922b3a53453501fd963ec7211')
        self.assertEqual(hashlib.sha256(self.raw_after).hexdigest(),
                         'e5826f94360264b722fc5364a382bec43d0b024a227d6a1938b8ed0c9d287b57')
        offset = self.after[6][0]
        self.assertEqual(self.patched[offset:offset + 5], self.original[offset:offset + 5])
        self.assertEqual(struct.unpack_from('<Q', self.patched, offset + 5)[0], 22038)

    def test_idempotence_and_file_api(self):
        self.assertEqual(PATCH.patched_bytes(self.patched), self.patched)
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            target = root / 'assets/res.dz.jpg'
            target.parent.mkdir()
            target.write_bytes(self.original)
            self.assertTrue(PATCH.apply(root))
            self.assertFalse(PATCH.apply(root))
            self.assertEqual(target.read_bytes(), self.patched)

    def test_tampered_original_or_patched_archive_is_rejected(self):
        for source in (self.original, self.patched):
            for offset in (0, self.table + 6 * 16, 40464, len(source) - 1):
                with self.subTest(length=len(source), offset=offset):
                    altered = bytearray(source)
                    altered[offset] ^= 1
                    with self.assertRaises(ValueError):
                        PATCH.patched_bytes(bytes(altered))
        for offset in (0, 0x5e6, 0x5f6, 0x65f, len(self.raw_before) - 1):
            altered = bytearray(self.raw_before)
            altered[offset] ^= 1
            with self.assertRaises(ValueError):
                PATCH.patched_resource_bytes(bytes(altered))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    if zipfile.is_zipfile(args.source):
        with zipfile.ZipFile(args.source) as archive:
            SOURCE = archive.read('assets/res.dz.jpg')
    else:
        SOURCE = args.source.read_bytes()
    unittest.main(argv=[__file__], verbosity=2)
