#!/usr/bin/env python3
"""Reconstruct a signed APK exactly from a pinned base and small literal data."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / '.publish/v0.1.15-flip3-socials'

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def assemble(staging, base, destination):
    manifest = json.loads((staging / 'manifest.json').read_text())
    assert manifest['format'] == 'zip-copy-delta-v1'
    assert Path(manifest['filename']).name == manifest['filename']
    assert Path(manifest['literal_filename']).name == manifest['literal_filename']
    assert base.stat().st_size == manifest['base_size']
    assert digest(base) == manifest['base_sha256']
    literals = (staging / manifest['literal_filename']).read_bytes()
    assert len(literals) == manifest['literal_size']
    assert hashlib.sha256(literals).hexdigest() == manifest['literal_sha256']
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / manifest['filename']
    total = 0
    state = hashlib.sha256()
    with base.open('rb') as original, output.open('wb') as target:
        for operation in manifest['operations']:
            assert len(operation) == 1
            kind = next(iter(operation))
            offset, size = operation[kind]
            assert isinstance(offset, int) and isinstance(size, int) and offset >= 0 and size > 0
            assert total + size <= manifest['size']
            if kind == 'copy':
                assert offset + size <= manifest['base_size']
                original.seek(offset)
                remaining = size
                while remaining:
                    block = original.read(min(remaining, 1024 * 1024))
                    assert block
                    target.write(block)
                    state.update(block)
                    remaining -= len(block)
            elif kind == 'literal':
                assert offset + size <= len(literals)
                block = literals[offset:offset + size]
                target.write(block)
                state.update(block)
            else: raise ValueError('Unknown operation ' + kind)
            total += size
    assert total == manifest['size'] and state.hexdigest() == manifest['sha256']
    (destination / 'SHA256SUMS').write_text(manifest['sha256'] + '  ' + manifest['filename'] + '\n')
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path)
    parser.add_argument('--destination', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    manifest = json.loads((STAGING / 'manifest.json').read_text())
    base = args.base
    if base is None:
        cache = ROOT / 'build/release-base'
        cache.mkdir(parents=True, exist_ok=True)
        base = cache / manifest['base_filename']
        if not base.exists() or digest(base) != manifest['base_sha256']:
            subprocess.run(['gh', 'release', 'download', manifest['base_tag'], '--repo',
                            'Russianranger/s3ce', '--dir', str(cache), '--pattern',
                            manifest['base_filename'], '--clobber'], check=True)
    print(assemble(STAGING, base, args.destination))
