#!/usr/bin/env python3
"""Resolve a source-controlled, candidate-bound opt-in for runtime QA."""
import json
import os
from pathlib import Path
import re
import time

from android_runtime_control import parse_control


def runtime_mode(event, dispatch_interactive, raw, candidate_sha256):
    mode = {'interactive': False, 'cold_start_attempts': 0}
    if raw is not None:
        document = parse_control(raw)
        if set(document) != {'schema', 'candidate_sha256', 'interactive', 'cold_start_attempts'}:
            raise ValueError('Runtime mode has missing or unexpected fields')
        if type(document['schema']) is not int or document['schema'] != 1:
            raise ValueError('Unsupported runtime mode schema')
        digest = document['candidate_sha256']
        if type(digest) is not str or not re.fullmatch(r'[0-9a-f]{64}', digest) or digest != candidate_sha256:
            raise ValueError('Runtime mode does not match the exact staged candidate')
        if type(document['interactive']) is not bool:
            raise ValueError('Runtime interactive mode must be a boolean')
        attempts = document['cold_start_attempts']
        if type(attempts) is not int or not 0 <= attempts <= 6:
            raise ValueError('Runtime cold starts must be an integer from 0 through 6')
        mode.update(interactive=document['interactive'], cold_start_attempts=attempts)
    if event == 'workflow_dispatch':
        if dispatch_interactive not in ('true', 'false', ''):
            raise ValueError('Invalid dispatch interactive choice')
        mode['interactive'] = dispatch_interactive == 'true'
    elif event != 'push':
        raise ValueError('Unsupported runtime workflow event')
    return mode


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / '.validation/runtime-mode.json'
    candidate = json.loads((root / '.validation/camera-input/manifest.json').read_text())
    mode = runtime_mode(os.environ['WORKFLOW_EVENT'], os.environ.get('DISPATCH_INTERACTIVE', ''),
                        path.read_bytes() if path.exists() else None, candidate['sha256'])
    with open(os.environ['GITHUB_ENV'], 'a') as stream:
        stream.write('S3CE_RUNTIME_INTERACTIVE=' + str(mode['interactive']).lower() + '\n')
        stream.write('S3CE_RUNTIME_COLD_START_ATTEMPTS=' + str(mode['cold_start_attempts']) + '\n')
        stream.write('S3CE_RUNTIME_DEADLINE_EPOCH=' + str(int(time.time()) + 4800) + '\n')
    print('Resolved runtime mode:', json.dumps(mode, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
