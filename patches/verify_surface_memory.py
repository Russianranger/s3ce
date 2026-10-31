#!/usr/bin/env python3
"""Execute actual surfaceChanged DEX with explicit host Android/JNI doubles."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile


def verify_guards(decoded):
    path = Path(__file__).resolve().parent / 'apply.py'
    spec = importlib.util.spec_from_file_location('s3ce_apply_memory_test', path)
    patch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patch)
    relative = 'smali/com/ideaworks3d/airplay/AirplayView.smali'
    source = (decoded / relative).read_text()
    corrected = patch.reduce_gl_bitmap(source)
    assert patch.reduce_gl_bitmap(corrected) == corrected
    cases = [source.replace('    .line 585', '    .line 1585', 1),
             corrected.replace('    if-nez v0, :s3ce_no_software_bitmap',
                               '    if-eqz v0, :s3ce_no_software_bitmap', 1),
             corrected.replace('    :s3ce_no_software_bitmap\n', '', 1).replace(
                               '    .line 587\n', '    .line 587\n    :s3ce_no_software_bitmap\n', 1)]
    for case in cases:
        try:
            patch.reduce_gl_bitmap(case)
        except ValueError:
            continue
        raise AssertionError('Tampered original or corrected method accepted')
    with tempfile.TemporaryDirectory(prefix='s3ce-surface-guards-') as directory:
        root = Path(directory)
        files = {row[0] for row in patch.PATCHES} | {row[0] for row in patch.METHOD_GUARDS}
        for name in files:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(decoded / name, target)
        patch.apply(root)
        once = {name: (root / name).read_bytes() for name in files}
        assert patch.apply(root) == []
        assert once == {name: (root / name).read_bytes() for name in files}
        target = root / relative
        target.write_text(target.read_text().replace('    .line 585', '    .line 1585', 1))
        before = {name: (root / name).read_bytes() for name in files}
        try:
            patch.apply(root)
        except ValueError as error:
            assert 'surfaceChanged' in str(error), str(error)
        else:
            raise AssertionError('Tampered method was accepted')
        assert before == {name: (root / name).read_bytes() for name in files}
    print('PASS: pinned surface guard, exact idempotence, changed opcode/anchor/target rejection, all-file no-write on failure.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', required=True, type=Path)
    parser.add_argument('--dexlib-jar', required=True, type=Path)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('--expect-original-bitmap', action='store_true')
    parser.add_argument('--decoded', type=Path, help='Also exercise patch guards against a decoded pinned source tree')
    args = parser.parse_args()
    if args.decoded:
        verify_guards(args.decoded)
    source = Path(__file__).resolve().parent / 'tests/SurfaceMemoryRegression.java'
    with tempfile.TemporaryDirectory(prefix='s3ce-surface-') as directory:
        subprocess.run([str(args.jdk / 'bin/javac'), '-cp', str(args.dexlib_jar),
                        '-d', directory, str(source)], check=True)
        subprocess.run([str(args.jdk / 'bin/java'), '-cp', directory + ':' + str(args.dexlib_jar.resolve()),
                        '-Ds3ce.test.apk=' + str(args.apk.resolve()),
                        '-Ds3ce.test.originalBitmap=' + str(args.expect_original_bitmap).lower(),
                        'SurfaceMemoryRegression'], check=True)

if __name__ == '__main__': main()
