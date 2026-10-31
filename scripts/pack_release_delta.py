#!/usr/bin/env python3
"""Stage a byte-exact APK update by reusing unchanged ZIP member data."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

def sha(data): return hashlib.sha256(data).hexdigest()

def data_offset(data, entry):
    start = entry.header_offset
    assert data[start:start + 4] == b'PK\x03\x04'
    name, extra = struct.unpack_from('<HH', data, start + 26)
    return start + 30 + name + extra

def _equal_edge(old, new, a, b, size, suffix=False):
    """Find a common edge using bounded C-level byte comparisons."""
    matched = 0
    while matched < size:
        count = min(65536, size - matched)
        def same(length):
            if suffix:
                return old[a - matched - length:a - matched] == new[b - matched - length:b - matched]
            return old[a + matched:a + matched + length] == new[b + matched:b + matched + length]
        if same(count):
            matched += count
            continue
        low, high = 0, count
        while low < high:
            middle = (low + high + 1) // 2
            if same(middle): low = middle
            else: high = middle - 1
        return matched + low
    return matched

def matching_member_spans(old, new, source, source_size, target, target_size):
    """Reuse identical portions of a changed STORED member after insertions.

    Archive directory edits and one replaced compressed resource must not turn
    the entire 26 MB resource archive into a literal upload. Matches are verified
    byte-for-byte and only affect release transport, never APK contents.
    """
    minimum = 4096
    spans = []
    def visit(a, end_a, b, end_b, depth):
        size = min(end_a - a, end_b - b)
        if size < minimum or depth >= 16: return
        prefix = _equal_edge(old, new, a, b, size)
        if prefix >= minimum: spans.append((b, a, prefix))
        a, b = a + prefix, b + prefix
        size = min(end_a - a, end_b - b)
        suffix = _equal_edge(old, new, end_a, end_b, size, True)
        if suffix >= minimum: spans.append((end_b - suffix, end_a - suffix, suffix))
        end_a, end_b = end_a - suffix, end_b - suffix
        if min(end_a - a, end_b - b) < minimum: return
        # Search a small, fixed set of anchors, then recurse around an exact
        # match. Work stays bounded even for unrelated/compressed input.
        room = end_b - b - minimum
        for numerator in (8, 4, 12, 2, 6, 10, 14, 0, 16):
            anchor = b + room * numerator // 16
            block = new[anchor:anchor + minimum]
            # A repeated padding block has many equally valid offsets. Prefer
            # a distinctive anchor so surrounding shifted data can be reused.
            if len(set(block)) < 8: continue
            match = old.find(block, a, end_a)
            if match < 0: continue
            spans.append((anchor, match, minimum))
            visit(a, match, b, anchor, depth + 1)
            visit(match + minimum, end_a, anchor + minimum, end_b, depth + 1)
            break
    visit(source, source + source_size, target, target + target_size, 0)
    return sorted(spans)

def pack(base, candidate, destination):
    old, new = base.read_bytes(), candidate.read_bytes()
    spans = []
    with zipfile.ZipFile(base) as before, zipfile.ZipFile(candidate) as after:
        for entry in after.infolist():
            try: prior = before.getinfo(entry.filename)
            except KeyError: continue
            if not entry.compress_size or entry.compress_type != prior.compress_type: continue
            source, target = data_offset(old, prior), data_offset(new, entry)
            size = entry.compress_size
            if size == prior.compress_size and old[source:source + size] == new[target:target + size]:
                spans.append((target, source, size))
            elif entry.compress_type == zipfile.ZIP_STORED and min(size, prior.compress_size) >= 65536:
                spans.extend(matching_member_spans(old, new, source, prior.compress_size, target, size))
    literals, operations, cursor = bytearray(), [], 0
    for target, source, size in sorted(spans):
        assert target >= cursor
        if target > cursor:
            operations.append({'literal': [len(literals), target - cursor]})
            literals.extend(new[cursor:target])
        operations.append({'copy': [source, size]})
        cursor = target + size
    if cursor < len(new):
        operations.append({'literal': [len(literals), len(new) - cursor]})
        literals.extend(new[cursor:])
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {'format': 'zip-copy-delta-v1', 'base_tag': 'v0.1.0-compat',
                'base_filename': base.name, 'base_size': len(old), 'base_sha256': sha(old),
                'filename': candidate.name, 'size': len(new), 'sha256': sha(new),
                'literal_filename': 'literals.bin', 'literal_size': len(literals),
                'literal_sha256': sha(literals), 'operations': operations}
    (destination / 'literals.bin').write_bytes(literals)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'candidate', 'destination'): p.add_argument(name, type=Path)
    a = p.parse_args()
    result = pack(a.base, a.candidate, a.destination)
    print(json.dumps({k: v for k, v in result.items() if k != 'operations'}, indent=2))
