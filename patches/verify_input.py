#!/usr/bin/env python3
"""Execute the APK touch method's DEX subset with Android input doubles.

The instruction interpreter rejects unknown bytecode and tests actual assembled
register/branch behavior. It does not emulate ART or the native engine. The
lifecycle test separately models the guarded resume wait with JVM latches.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', required=True, type=Path)
    parser.add_argument('--dexlib-jar', required=True, type=Path, help='JAR containing full dexlib2 API, e.g. the audited JADX headless JAR')
    parser.add_argument('--jdk', required=True, type=Path)
    args = parser.parse_args()
    tests = Path(__file__).resolve().parent / 'tests'
    java, javac = args.jdk / 'bin/java', args.jdk / 'bin/javac'
    def run(*command):
        subprocess.run([str(v) for v in command], check=True)
    with tempfile.TemporaryDirectory(prefix='s3ce-input-') as work:
        work = Path(work)
        output = work / 'classes'
        output.mkdir()
        run(javac, '-cp', args.dexlib_jar, '-d', output, tests / 'MultiTouch.java',
            tests / 'MotionEvent.java', tests / 'AirplayView.java',
            tests / 'TouchRegression.java', tests / 'LifecycleRace.java')
        run(java, '-cp', str(output) + ':' + str(args.dexlib_jar.resolve()),
            '-Ds3ce.test.apk=' + str(args.apk.resolve()), 'com.ideaworks3d.airplay.TouchRegression')
        run(java, '-cp', output, 'LifecycleRace')


if __name__ == '__main__':
    main()
