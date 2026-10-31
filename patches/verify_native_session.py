#!/usr/bin/env python3
"""Exercise the candidate's assembled native-run diagnostic markers."""
import argparse
from pathlib import Path
import subprocess
import tempfile

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', required=True, type=Path)
    parser.add_argument('--dexlib-jar', required=True, type=Path)
    parser.add_argument('--jdk', required=True, type=Path)
    args = parser.parse_args()
    tests = Path(__file__).resolve().parent / 'tests'
    with tempfile.TemporaryDirectory(prefix='s3ce-native-session-') as work:
        subprocess.run([str(args.jdk / 'bin/javac'), '-cp', str(args.dexlib_jar), '-d', work,
                        *[str(tests / name) for name in ['MultiTouch.java', 'MotionEvent.java', 'AirplayView.java',
                                                        'NativeSessionRegression.java']]], check=True)
        subprocess.run([str(args.jdk / 'bin/java'), '-cp', work + ':' + str(args.dexlib_jar.resolve()),
                        '-Ds3ce.test.apk=' + str(args.apk.resolve()),
                        'com.ideaworks3d.airplay.NativeSessionRegression'], check=True)

if __name__ == '__main__':
    main()
