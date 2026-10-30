#!/usr/bin/env python3
"""Reassemble connector-staged release bytes and verify all digests."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
staging = root / '.publish/v0.1.0-compat'
manifest = json.loads((staging / 'manifest.json').read_text())
assert Path(manifest['filename']).name == manifest['filename']
destination = root / 'dist'
destination.mkdir(exist_ok=True)
output = destination / manifest['filename']
hash_state = hashlib.sha256()
total = 0
if all((staging / part['filename']).is_file() for part in manifest['parts']):
    with output.open('wb') as target:
        for part in manifest['parts']:
            assert Path(part['filename']).name == part['filename']
            content = (staging / part['filename']).read_bytes()
            assert len(content) == part['size']
            assert hashlib.sha256(content).hexdigest() == part['sha256']
            target.write(content)
            hash_state.update(content)
            total += len(content)
else:
    # Temporary transfer chunks are removed after successful publication.
    # Later CI retries verify the published asset against the pinned manifest.
    subprocess.run(['gh', 'release', 'download', 'v0.1.0-compat', '--repo',
                    'Russianranger/s3ce', '--dir', str(destination), '--pattern',
                    manifest['filename'], '--clobber'], check=True)
    with output.open('rb') as downloaded:
        for content in iter(lambda: downloaded.read(1024 * 1024), b''):
            hash_state.update(content)
            total += len(content)
assert total == manifest['size']
assert hash_state.hexdigest() == manifest['sha256']
(destination / 'SHA256SUMS').write_text(manifest['sha256'] + '  ' + manifest['filename'] + '\n')
print(output)
