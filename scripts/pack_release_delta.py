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

def pack(base, candidate, destination):
    old, new = base.read_bytes(), candidate.read_bytes()
    spans = []
    with zipfile.ZipFile(base) as before, zipfile.ZipFile(candidate) as after:
        for entry in after.infolist():
            try: prior = before.getinfo(entry.filename)
            except KeyError: continue
            if not entry.compress_size or entry.compress_type != prior.compress_type: continue
            if entry.compress_size != prior.compress_size: continue
            source, target = data_offset(old, prior), data_offset(new, entry)
            size = entry.compress_size
            if old[source:source + size] == new[target:target + size]:
                spans.append((target, source, size))
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
