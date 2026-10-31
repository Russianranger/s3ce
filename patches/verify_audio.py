#!/usr/bin/env python3
"""Execute actual assembled SoundPlayer DEX with bounded host AudioTrack doubles.

This checks register/control-flow, exception handlers and explicit reentrant
monitors; it is not ART, the Android audio service, or native mixer emulation.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', required=True, type=Path,
                        help='APK or assembled DEX containing patched SoundPlayer')
    parser.add_argument('--dexlib-jar', required=True, type=Path)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('--expect-original-race', action='store_true',
                        help='Counterexample: original late callback must generate after stop then throw NPE')
    args = parser.parse_args()
    source = Path(__file__).resolve().parent / 'tests' / 'SoundPlayerRegression.java'
    with tempfile.TemporaryDirectory(prefix='s3ce-audio-') as directory:
        output = Path(directory)
        subprocess.run([str(args.jdk / 'bin/javac'), '-cp', str(args.dexlib_jar),
                        '-d', str(output), str(source)], check=True)
        subprocess.run([str(args.jdk / 'bin/java'), '-cp',
                        str(output) + ':' + str(args.dexlib_jar.resolve()),
                        '-Ds3ce.test.apk=' + str(args.apk.resolve()),
                        '-Ds3ce.test.originalRace=' + str(args.expect_original_race).lower(),
                        'SoundPlayerRegression'], check=True)


if __name__ == '__main__':
    main()
