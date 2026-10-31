#!/usr/bin/env python3
"""Assemble signed internal APKs without keys or release publication."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from assemble_release import assemble

ROOT = Path(__file__).resolve().parents[1]


def main():
    cache = ROOT / 'build/runtime-internal/base'
    cache.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for label, staging in [('candidate', ROOT / '.validation/camera-input'),
                           ('baseline', ROOT / '.publish/v0.1.12-hud-startup')]:
        manifest = json.loads((staging / 'manifest.json').read_text())
        base = cache / manifest['base_filename']
        if not base.exists() or hashlib.file_digest(base.open('rb'), 'sha256').hexdigest() != manifest['base_sha256']:
            subprocess.run(['gh', 'release', 'download', manifest['base_tag'], '--repo',
                            'Russianranger/s3ce', '--dir', str(cache), '--pattern',
                            manifest['base_filename'], '--clobber'], check=True)
        apk = assemble(staging, base, ROOT / 'build/runtime-internal' / label)
        outputs[label] = str(apk)
        print(f'{label}: {apk.name} sha256={manifest["sha256"]}', flush=True)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.writelines(f'{key}={value}\n' for key, value in outputs.items())
    return outputs


if __name__ == '__main__':
    main()
