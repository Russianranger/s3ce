#!/usr/bin/env python3
"""Run the production GL file logger on the JVM with Android Log as the only double."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('--sdk', required=True, type=Path)
    args = parser.parse_args()
    tests = Path(__file__).resolve().parent
    source = tests.parent / 'src'
    android = args.sdk / 'platforms/android-35/android.jar'
    with tempfile.TemporaryDirectory(prefix='s3ce-gl-log-test-') as work:
        subprocess.run([str(args.jdk / 'bin/javac'), '--release', '8', '-classpath', str(android),
                        '-d', work, str(tests / 'android/util/Log.java'), str(tests / 'GlLogRegression.java'),
                        *map(str, sorted(source.rglob('*.java')))], check=True)
        subprocess.run([str(args.jdk / 'bin/java'), '-classpath', work + ':' + str(android),
                        'com.ideaworks3d.thesims3.GlLogRegression'], check=True)


if __name__ == '__main__':
    main()
