#!/usr/bin/env python3
"""Add ordinary romance progression from Good Friend and Best Friend.

Only two relationship graph edges are appended to the pinned simsdata.bin.
Existing edges retain first-match priority. Action acceptance, traits, pairing,
later romantic stages and save representation stay in the original engine.

The enclosing DTRZ archive keeps every other compressed resource byte intact.
Whole-file fingerprints reject unrelated versions or an unintended asset patch.
"""
from __future__ import annotations

import argparse
import hashlib
import lzma
from pathlib import Path
import struct

ORIGINAL_SHA256 = '3bbb04b058f245b1784370270f26a547ac36d124ef26d09fbadac05ee2dfcf82'
ORIGINAL_RESOURCE_SHA256 = '778c385d6ee62e48bacfea06d5a61b71d1caced5a68b45edaf3cfdb1801511f4'
PATCHED_SHA256 = '82357d3082b520ebcc583ff2526fc6066c51d39922b3a53453501fd963ec7211'
PATCHED_RESOURCE_SHA256 = 'e5826f94360264b722fc5364a382bec43d0b024a227d6a1938b8ed0c9d287b57'
ENTRY_INDEX = 6
ENTRY_COUNT = 678
GRAPH_START = 0x57f
GRAPH_END = 0x65f
ROMANCE_EDGE = struct.pack('>BBh', 8, 1, 10)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError('Unexpected relationship tuning structure: ' + message)


def _entry(data: bytes) -> tuple[int, int, int]:
    _require(data[:4] == b'DTRZ', 'archive magic')
    count, directories = struct.unpack_from('<HH', data, 4)
    _require((count, directories) == (ENTRY_COUNT, 15), 'archive counts')
    cursor, names = 8, []
    for _ in range(count + directories):
        end = data.index(0, cursor)
        names.append(data[cursor:end])
        cursor = end + 1
    _require(names[0] == b'' and names[ENTRY_INDEX + 1] == b'simsdata.bin', 'entry name')
    _require(struct.unpack_from('<HHH', data, cursor + ENTRY_INDEX * 6) ==
             (1, ENTRY_INDEX, 0xffff), 'entry links')
    cursor += count * 6
    _require(struct.unpack_from('<HH', data, cursor) == (1, count), 'record table header')
    record = cursor + 4 + ENTRY_INDEX * 16
    _require(struct.unpack_from('<4I', data, record) == (40464, 22030, 22030, 0x200),
             'entry metadata')
    end = struct.unpack_from('<I', data, record + 16)[0]
    _require(end == 48441, 'compressed entry extent')
    return record, 40464, end


def patched_resource_bytes(original: bytes) -> bytes:
    """Change exactly two counts and append two four-byte transitions."""
    _require(hashlib.sha256(original).hexdigest() == ORIGINAL_RESOURCE_SHA256,
             'original simsdata hash')
    _require(original[GRAPH_START - 2:GRAPH_START] == bytes((2, 15)),
             'score-channel/state counts')
    cursor, sections = GRAPH_START, []
    for state in range(15):
        header = original[cursor:cursor + 8]
        count = header[7]
        cursor += 8
        edges = original[cursor:cursor + count * 4]
        cursor += count * 4
        if state in (6, 7):
            expected = (bytes.fromhex('0500fff607000019') if state == 6
                        else bytes.fromhex('0600fff1'))
            _require(edges == expected, 'original Good/Best Friend edge ordering')
            header = header[:7] + bytes((count + 1,))
            edges += ROMANCE_EDGE
        sections.append(header + edges)
    _require(cursor == GRAPH_END, 'original graph extent')
    result = original[:GRAPH_START] + b''.join(sections) + original[GRAPH_END:]
    _require(len(result) == len(original) + 8, 'patched resource length')
    _require(hashlib.sha256(result).hexdigest() == PATCHED_RESOURCE_SHA256,
             'patched simsdata hash')
    return result


def _patch_original(original: bytes) -> bytes:
    record, start, end = _entry(original)
    raw = lzma.decompress(original[start:end], format=lzma.FORMAT_ALONE)
    patched = patched_resource_bytes(raw)
    # Retain DTRZ's LZMA1 properties: 64 KiB dictionary, LC3/LP0/PB2, known size.
    compressed = lzma.compress(patched, format=lzma.FORMAT_ALONE, filters=[{
        'id': lzma.FILTER_LZMA1, 'dict_size': 65536, 'lc': 3, 'lp': 0, 'pb': 2,
        'mode': lzma.MODE_NORMAL, 'nice_len': 273, 'mf': lzma.MF_BT4, 'depth': 0,
    }])
    compressed = compressed[:5] + struct.pack('<Q', len(patched)) + compressed[13:]
    _require(lzma.decompress(compressed, format=lzma.FORMAT_ALONE) == patched,
             'replacement round trip')
    delta = len(compressed) - (end - start)
    result = bytearray(original[:start] + compressed + original[end:])
    struct.pack_into('<4I', result, record, start, len(patched), len(patched), 0x200)
    previous = start
    for index in range(ENTRY_INDEX + 1, ENTRY_COUNT):
        position = record + (index - ENTRY_INDEX) * 16
        offset = struct.unpack_from('<I', original, position)[0]
        _require(previous < offset < len(original), 'ordered original payload offsets')
        struct.pack_into('<I', result, position, offset + delta)
        previous = offset
    return bytes(result)


def patched_bytes(original: bytes) -> bytes:
    """Accept only the pinned original or this exact, idempotent result."""
    digest = hashlib.sha256(original).hexdigest()
    if digest == PATCHED_SHA256:
        return original
    if digest != ORIGINAL_SHA256:
        raise ValueError('Unexpected res.dz bytes; refusing relationship tuning patch')
    result = _patch_original(original)
    _require(hashlib.sha256(result).hexdigest() == PATCHED_SHA256,
             'deterministic patched archive hash')
    return result


def apply(decoded: Path) -> bool:
    target = decoded / 'assets/res.dz.jpg'
    original = target.read_bytes()
    result = patched_bytes(original)
    if result == original:
        return False
    target.write_bytes(result)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded', type=Path)
    args = parser.parse_args()
    print('Friendship romance transitions: ' + ('patched' if apply(args.decoded) else 'already patched'))
