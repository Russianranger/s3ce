#!/usr/bin/env python3
"""Run production bootstrap ownership/admission Java with explicit host boundaries."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / 'app/src/com/ideaworks3d/thesims3'
    fixtures = root / 'patches/tests/runtime_boot'
    with tempfile.TemporaryDirectory(prefix='s3ce-bootstrap-host-') as temporary:
        directory = Path(temporary)
        classes = directory / 'classes'
        classes.mkdir()
        subprocess.run([str(args.jdk / 'bin/javac'), '--release', '8', '-d', str(classes),
                        str(source / 'RuntimeBootstrap.java'), str(source / 'GameBootActivity.java'),
                        *map(str, sorted(fixtures.rglob('*.java')))], check=True)
        for scenario in ('gate', 'normal', 'original', 'restored-failure', 'boot-failure'):
            # Each process has its own readiness, failure cache, and file directory.
            files = directory / scenario
            files.mkdir()
            subprocess.run([str(args.jdk / 'bin/java'), '-cp', str(classes),
                            '-Djava.library.path=' + str(directory / 'no-native-library'),
                            '-Ds3ce.test.files=' + str(files),
                            'com.ideaworks3d.thesims3.RuntimeBootstrapContract', scenario], check=True)
    print('PASS: production Java bootstrap owner/admission/failure UI; Android/native/prefs are host boundaries.')


if __name__ == '__main__':
    main()
