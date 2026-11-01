#!/usr/bin/env python3
"""Check assembled viewport installation/orientation DEX and guarded patch source.

Host ViewGroup contracts and real Android platform execution are separate checks.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk',required=True,type=Path)
    parser.add_argument('--dexlib-jar',required=True,type=Path)
    parser.add_argument('--jdk',required=True,type=Path)
    args=parser.parse_args()
    android='{http://schemas.android.com/apk/res/android}'
    manifest=ET.parse(ROOT/'app/AndroidManifest.xml')
    activity=next(a for a in manifest.findall('./application/activity')
                  if a.get(android+'name')=='com.ideaworks3d.thesims3.Main')
    assert activity.get(android+'screenOrientation')=='sensorLandscape'
    entries=json.loads((ROOT/'patches/viewport_methods.json').read_text())
    assert len(entries)==1 and entries[0][1]=='fixOrientation(I)V'
    patched=(ROOT/'patches/methods'/entries[0][3]).read_text().rstrip('\n')
    old=patched.replace('    # S3CE Flip3: retain sensor-selected normal/reverse landscape.\n    const/4 v1, 0x6\n','    const/4 v1, 0x0\n')
    assert hashlib.sha256(old.encode()).hexdigest()==entries[0][2], 'orientation patch changed outside one constant'
    with tempfile.TemporaryDirectory(prefix='s3ce-viewport-dex-')as directory:
        classes=Path(directory)/'classes';classes.mkdir()
        subprocess.run([str(args.jdk/'bin/javac'),'-cp',str(args.dexlib_jar),'-d',str(classes),
                        str(ROOT/'patches/tests/ViewportDexRegression.java')],check=True)
        subprocess.run([str(args.jdk/'bin/java'),'-cp',str(classes)+':'+str(args.dexlib_jar.resolve()),
                        '-Ds3ce.test.apk='+str(args.apk.resolve()),
                        'com.ideaworks3d.airplay.ViewportDexRegression'],check=True)

if __name__=='__main__':main()
