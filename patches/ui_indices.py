#!/usr/bin/env python3
"""Represent the pinned UI quad strip with explicit, equivalent indices.

The original anim2d.m3g has 530 meshes sharing one implicit TriangleStripArray:
first vertex 0, one strip of length 4.  Only that object's representation changes
to explicit indices [0, 1, 2, 3].  Meshes, positions, UVs, textures and strip
topology remain byte-identical.  This exercises the existing indexed draw path
as a compatibility candidate for modern drivers; it does not alter input.

The replacement LZMA payload occupies the original entry's position in res.dz.
Later directory offsets shift by its compressed-size difference, preserving
their order and every other compressed payload byte.  Whole-file hashes reject
other game versions and tampering, and make the patch idempotent.
"""
from __future__ import annotations

import argparse
import hashlib
import lzma
from pathlib import Path
import struct
import zlib

ORIGINAL_SHA256 = "3bbb04b058f245b1784370270f26a547ac36d124ef26d09fbadac05ee2dfcf82"
ORIGINAL_M3G_SHA256 = "d2cd083b6cdb5132a3de8dee171526b91d28894d8742c001ab2b77e06438b779"
PATCHED_SHA256 = "fb9d27d61e2cf665c2d2cafb8a837424c9376fbb833a2b37bbb83ccc5415a124"
PATCHED_M3G_SHA256 = "a1a82bb23197cb1801684d5313faeb312c1be46e7dc25bbd189c4445d8a0506a"
ENTRY_INDEX = 104
ORIGINAL_TSA = bytes.fromhex("00000000000000000000000001000100000004000000")
EXPLICIT_TSA = bytes(12) + b"\x81" + struct.pack("<I", 4) + bytes(range(4)) + struct.pack("<II", 1, 4)
M3G_MAGIC = b"\xabJSR184\xbb\r\n\x1a\n"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("Unexpected UI asset structure: " + message)


def _entry(data: bytes) -> tuple[int, int, int]:
    """Return the pinned entry's record offset and compressed payload bounds."""
    _require(data[:4] == b"DTRZ", "archive magic")
    count, directory_count = struct.unpack_from("<HH", data, 4)
    _require((count, directory_count) == (678, 15), "archive counts")
    cursor = 8
    strings = []
    for _ in range(count + directory_count):
        end = data.index(0, cursor)
        strings.append(data[cursor:end])
        cursor = end + 1
    _require(strings[0] == b"" and strings[ENTRY_INDEX + 1] == b"anim2d.m3g", "entry name")
    directory, name, parent = struct.unpack_from("<HHH", data, cursor + ENTRY_INDEX * 6)
    _require((directory, name, parent) == (0, ENTRY_INDEX, 0xFFFF), "entry links")
    cursor += count * 6
    _require(struct.unpack_from("<HH", data, cursor) == (1, count), "record table header")
    table = cursor + 4
    record = table + ENTRY_INDEX * 16
    offset, size, duplicate_size, flags = struct.unpack_from("<4I", data, record)
    next_offset = struct.unpack_from("<I", data, record + 16)[0]
    _require((offset, size, duplicate_size, flags) == (1593019, 141632, 141632, 0x200), "entry metadata")
    _require(next_offset == offset + 9789, "entry extent")
    return record, offset, next_offset


def _objects(payload: bytes) -> list[tuple[int, bytes]]:
    result = []
    cursor = 0
    while cursor < len(payload):
        _require(cursor + 5 <= len(payload), "object header bounds")
        kind, size = struct.unpack_from("<BI", payload, cursor)
        cursor += 5
        _require(cursor + size <= len(payload), "object bounds")
        result.append((kind, payload[cursor:cursor + size]))
        cursor += size
    return result


def _section(payload: bytes) -> bytes:
    body = struct.pack("<BII", 0, len(payload) + 13, len(payload)) + payload
    return body + struct.pack("<I", zlib.adler32(body))


def patched_m3g_bytes(original: bytes) -> bytes:
    """Patch only the pinned raw anim2d object and its required size/checksums."""
    _require(hashlib.sha256(original).hexdigest() == ORIGINAL_M3G_SHA256, "raw anim2d hash")
    _require(original[:12] == M3G_MAGIC, "M3G magic")
    cursor = 12
    sections = []
    while cursor < len(original):
        compression, size, uncompressed = struct.unpack_from("<BII", original, cursor)
        _require(compression == 0 and size >= 13, "uncompressed section")
        end = cursor + size
        _require(end <= len(original), "section bounds")
        _require(uncompressed == size - 13, "section lengths")
        expected = struct.unpack_from("<I", original, end - 4)[0]
        _require(zlib.adler32(original[cursor:end - 4]) == expected, "section checksum")
        sections.append(_objects(original[cursor + 9:end - 4]))
        cursor = end
    _require(len(sections) == 2 and len(sections[0]) == 1, "section/object layout")
    _require(sum(len(section) for section in sections) == 2500, "object count")
    _require(sum(kind == 14 for section in sections for kind, _ in section) == 530, "sprite count")
    _require(sections[0][0][0] == 0, "header object")
    header = bytearray(sections[0][0][1])
    _require(header[:3] == b"\x01\x00\x00", "M3G version/external references")
    _require(struct.unpack_from("<II", header, 3) == (len(original), len(original)), "header sizes")
    changes = 0
    object_number = 0
    rebuilt = []
    for section in sections:
        payload = bytearray()
        for kind, body in section:
            object_number += 1
            if kind == 0:
                body = bytes(header[:3]) + struct.pack("<II", len(original) + 7, len(original) + 7) + bytes(header[11:])
            elif kind == 11:
                _require(object_number == 5 and body == ORIGINAL_TSA, "shared TriangleStripArray")
                body = EXPLICIT_TSA
                changes += 1
            payload += struct.pack("<BI", kind, len(body)) + body
        rebuilt.append(_section(bytes(payload)))
    _require(changes == 1, "single shared strip")
    result = M3G_MAGIC + b"".join(rebuilt)
    _require(len(result) == len(original) + 7, "patched M3G length")
    _require(hashlib.sha256(result).hexdigest() == PATCHED_M3G_SHA256, "patched anim2d hash")
    return result


def _patch_original(original: bytes) -> bytes:
    record, start, end = _entry(original)
    raw = lzma.decompress(original[start:end], format=lzma.FORMAT_ALONE)
    patched = patched_m3g_bytes(raw)
    # Explicit filter settings make this deterministic and retain the original
    # archive's 64 KiB LZMA dictionary/LC/LP/PB properties.
    compressed = lzma.compress(patched, format=lzma.FORMAT_ALONE, filters=[{
        "id": lzma.FILTER_LZMA1, "dict_size": 65536, "lc": 3, "lp": 0, "pb": 2,
        "mode": lzma.MODE_NORMAL, "nice_len": 273, "mf": lzma.MF_BT4, "depth": 0,
    }])
    # FORMAT_ALONE permits a known uncompressed length, as used by DTRZ.
    compressed = compressed[:5] + struct.pack("<Q", len(patched)) + compressed[13:]
    _require(lzma.decompress(compressed, format=lzma.FORMAT_ALONE) == patched, "replacement round trip")
    delta = len(compressed) - (end - start)
    result = bytearray(original[:start] + compressed + original[end:])
    struct.pack_into("<4I", result, record, start, len(patched), len(patched), 0x200)
    previous = start
    for index in range(ENTRY_INDEX + 1, 678):
        position = record + (index - ENTRY_INDEX) * 16
        offset = struct.unpack_from("<I", original, position)[0]
        _require(previous < offset < len(original), "ordered original payload offsets")
        struct.pack_into("<I", result, position, offset + delta)
        previous = offset
    return bytes(result)


def patched_bytes(original: bytes) -> bytes:
    """Accept only the original archive or this exact, idempotent patch result."""
    digest = hashlib.sha256(original).hexdigest()
    if digest == PATCHED_SHA256:
        return original
    if digest != ORIGINAL_SHA256:
        raise ValueError("Unexpected res.dz bytes; refusing the version-specific UI index patch")
    result = _patch_original(original)
    _require(hashlib.sha256(result).hexdigest() == PATCHED_SHA256, "deterministic patched archive hash")
    return result


def apply(decoded: Path) -> bool:
    target = decoded / "assets" / "res.dz.jpg"
    original = target.read_bytes()
    result = patched_bytes(original)
    if result == original:
        return False
    target.write_bytes(result)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decoded", type=Path)
    args = parser.parse_args()
    print("Explicit UI quad indices: " + ("patched" if apply(args.decoded) else "already patched"))
