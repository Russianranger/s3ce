#!/usr/bin/env python3
"""Wait for a frame from the persistent Android controller; no device access."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from android_runtime_control import MAX_INTERACTIVE_COMMANDS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('build/runtime-evidence'))
    parser.add_argument('--frame', type=int)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--finish', action='store_true')
    args = parser.parse_args()
    if not args.finish and (args.frame is None or not 0 <= args.frame < MAX_INTERACTIVE_COMMANDS):
        parser.error(f'frame must be 0..{MAX_INTERACTIVE_COMMANDS - 1}')
    deadline = time.monotonic() + args.timeout
    marker = args.output / 'live/controller-exit.json'
    ready = args.output / f'live/ready-{args.frame:03d}.json' if not args.finish else None
    while time.monotonic() < deadline:
        if ready and ready.is_file():
            metadata = json.loads(ready.read_text())
            frame = args.output / f'live/frame-{args.frame:03d}'
            if not (frame / 'screen.png').is_file() or not (frame / 'frame.json').is_file():
                raise RuntimeError('Frame marker exists without screenshot/metadata')
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write('available=true\nframe_path=' + str(frame) + '\n')
            print(json.dumps(metadata), flush=True)
            return
        if marker.is_file():
            state = json.loads(marker.read_text())
            print(json.dumps({'controller_exit': state}), flush=True)
            if args.finish:
                sys.exit(int(state['exit_code']))
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write('available=false\n')
            return
        runner_temp = os.environ.get('RUNNER_TEMP')
        pid_file = Path(runner_temp) / 's3ce-runtime-controller.pid' if runner_temp else None
        if pid_file and pid_file.is_file():
            pid = pid_file.read_text().strip()
            if not pid.isdecimal():
                raise RuntimeError('Invalid controller PID marker')
            try:
                os.kill(int(pid), 0)
            except ProcessLookupError as error:
                raise RuntimeError('Controller exited without its result marker; inspect controller.log') from error
        time.sleep(2)
    raise TimeoutError('Timed out waiting for ' + ('controller completion' if args.finish else f'live frame{args.frame}'))


if __name__ == '__main__':
    main()
