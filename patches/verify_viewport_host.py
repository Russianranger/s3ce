#!/usr/bin/env python3
"""Compile the production viewport against bounded Android JVM contracts.

Doubles model parent/child routing and lifecycle signals, not Android, EGL, ART,
or hardware. A separate exact-APK Android probe owns real-platform evidence.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', type=Path, required=True)
    parser.add_argument('--source', type=Path, help='Optional archived production source for counterexamples')
    parser.add_argument('--case', choices=('all', 'ownership'), default='all')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = args.source or root / 'app/src/com/ideaworks3d/thesims3/GameViewport.java'
    fixtures = root / 'patches/tests/viewport'
    with tempfile.TemporaryDirectory(prefix='s3ce-viewport-host-') as temporary:
        classes = Path(temporary) / 'classes'
        classes.mkdir()
        subprocess.run([str(args.jdk / 'bin/javac'), '--release', '8', '-d', str(classes),
                        str(source), *(str(p) for p in sorted(fixtures.rglob('*.java')))], check=True)
        for sdk in (26, 28, 30, 35):
            subprocess.run([str(args.jdk / 'bin/java'), '-Ds3ce.viewport.work=' + temporary, '-cp', str(classes),
                            'com.ideaworks3d.thesims3.ViewportContract', str(sdk), args.case], check=True)


if __name__ == '__main__':
    main()
