#!/usr/bin/env python3
"""Fail-closed viewport patches using copied decoded candidate bridge files."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import shutil
import tempfile
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('s3ce_apply',ROOT/'patches/apply.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def snapshots(directory):
    return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*.smali')}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decoded',required=True,type=Path);args=parser.parse_args()
    targets={p[0]for p in patch.PATCHES}|{p[0]for p in patch.METHOD_GUARDS}
    with tempfile.TemporaryDirectory(prefix='s3ce-viewport-guards-')as tmp:
        directory=Path(tmp)
        for relative in targets:
            target=directory/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(args.decoded/relative,target)
        assert patch.apply(directory)==[], 'Candidate patching must be idempotent'
        intact=snapshots(directory)
        cases=[('smali/com/ideaworks3d/airplay/AirplayThread.smali',
                '    const/4 v1, 0x6\n','    const/4 v1, 0x5\n'),
               ('smali/com/ideaworks3d/airplay/AirplayActivity.smali',
                'Lcom/ideaworks3d/thesims3/GameViewport;->install',
                'Lcom/ideaworks3d/thesims3/GameViewport;->unreviewedInstall')]
        for relative,old,new in cases:
            target=directory/relative;source=target.read_text();assert source.count(old)==1
            target.write_text(source.replace(old,new,1));tampered=snapshots(directory)
            try:patch.apply(directory)
            except ValueError:pass
            else:raise AssertionError('Unknown viewport/orientation method accepted')
            assert snapshots(directory)==tampered, 'Refusal must precede all file writes'
            target.write_text(source);assert snapshots(directory)==intact
    print('PASS viewport repeat application and two atomic unknown-method refusals')
if __name__=='__main__':main()
