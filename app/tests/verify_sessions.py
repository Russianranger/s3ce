#!/usr/bin/env python3
"""Run production session-history persistence and export on a host JVM."""
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
    source = tests.parent / 'src/com/ideaworks3d/thesims3'
    android = args.sdk / 'platforms/android-35/android.jar'
    with tempfile.TemporaryDirectory(prefix='s3ce-session-java-') as work:
        subprocess.run([str(args.jdk / 'bin/javac'), '--release', '8', '-classpath', str(android),
                        '-d', work, str(source / 'SessionDiagnostics.java'), str(source / 'ExitReport.java'),
                        str(source / 'NativeTombstoneSummary.java'),
                        str(tests / 'com/ideaworks3d/thesims3/SessionDiagnosticsRegression.java')], check=True)
        subprocess.run([str(args.jdk / 'bin/java'), '-classpath', work + ':' + str(android),
                        'com.ideaworks3d.thesims3.SessionDiagnosticsRegression'], check=True)

if __name__ == '__main__':
    main()
