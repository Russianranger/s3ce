#!/usr/bin/env python3
"""Exact startup bridge applicability, idempotence and atomic refusal boundaries."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('s3ce_apply', ROOT / 'patches/apply.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


def snapshots(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob('*.smali')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decoded', required=True, type=Path)
    args = parser.parse_args()
    targets = {entry[0] for entry in patch.PATCHES} | {entry[0] for entry in patch.METHOD_GUARDS}
    with tempfile.TemporaryDirectory(prefix='s3ce-runtime-guards-') as temporary:
        directory = Path(temporary)
        for relative in targets:
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.decoded / relative, target)
        patch.apply(directory)
        assert patch.apply(directory) == [], 'Exact repeated startup patching must be idempotent'
        intact = snapshots(directory)
        activity = directory / 'smali/com/ideaworks3d/airplay/AirplayActivity.smali'
        source = activity.read_text()
        cases = [('onCreate(Landroid/os/Bundle;)V', '->prepareMain(', '->unreviewedPrepare('),
                 ('onStart()V', '->canStartMain(', '->unreviewedAdmission('),
                 ('onCreate(Landroid/os/Bundle;)V', 'if-eqz v0, :s3ce_runtime_not_ready',
                  'if-nez v0, :s3ce_runtime_not_ready'),
                 ('onStart()V', 'if-eqz v0, :s3ce_runtime_not_ready',
                  'if-nez v0, :s3ce_runtime_not_ready')]
        for signature, before, after in cases:
            matches = patch.method_matches(source, signature)
            assert len(matches) == 1
            method = matches[0].group()
            assert method.count(before) == 1
            activity.write_text(source[:matches[0].start()] + method.replace(before, after, 1)
                                + source[matches[0].end():])
            tampered = snapshots(directory)
            try:
                patch.apply(directory)
            except ValueError:
                pass
            else:
                raise AssertionError('Unknown or reversed startup boundary accepted')
            assert snapshots(directory) == tampered, 'Refusal must precede every file write'
            activity.write_text(source)
            assert snapshots(directory) == intact
    print('PASS startup applicability/idempotence and four atomic unknown/reversed-boundary refusals')


if __name__ == '__main__':
    main()
