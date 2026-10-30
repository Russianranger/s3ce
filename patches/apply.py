#!/usr/bin/env python3
"""Patch the pinned APK's Android bridge without shipping decompiled classes.

Sensitive optional S3E services return their existing failure sentinels. The
engine already uses getFilesDir for its primary save root; its optional card root
is redirected there too. Device ID is Android's app/signing-key/user-scoped ID.
The removed hidden PowerManager call uses a public Window API helper instead.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import re

# File, exact method signature, SHA-256 of original method, replacement.
PATCHES = [('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'getCardRoot()Ljava/lang/String;',
  '0f4bf08c5fac48942db40e43e62a46af20f1db433117bdbd40fd15e7864cfb0a',
  '.method private getCardRoot()Ljava/lang/String;\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_FileRoot:Ljava/io/File;\n'
  '    invoke-virtual {v0}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;\n'
  '    move-result-object v0\n'
  '    return-object v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'getDeviceId()Ljava/lang/String;',
  'aa5d2223aa3ad37d6d50a1548e4ef03fe0bf0917be5d96c0b403ab01dad4419d',
  '.method public getDeviceId()Ljava/lang/String;\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 2\n'
  '    iget-object v0, p0, '
  'Lcom/ideaworks3d/airplay/AirplayThread;->m_Airplay:Lcom/ideaworks3d/airplay/AirplayActivity;\n'
  '    invoke-virtual {v0}, '
  'Lcom/ideaworks3d/airplay/AirplayActivity;->getContentResolver()Landroid/content/ContentResolver;\n'
  '    move-result-object v0\n'
  '    const-string v1, "android_id"\n'
  '    invoke-static {v0, v1}, '
  'Landroid/provider/Settings$Secure;->getString(Landroid/content/ContentResolver;Ljava/lang/String;)Ljava/lang/String;\n'
  '    move-result-object v0\n'
  '    if-nez v0, :s3ce_identifier_ready\n'
  '    const-string v0, "s3ce-local-install"\n'
  '    :s3ce_identifier_ready\n'
  '    return-object v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'getDeviceNumber()Ljava/lang/String;',
  'b068cf4986f23686f36a62e2cd4dd55d60fce94b839faeb3a87424b757dbef26',
  '.method public getDeviceNumber()Ljava/lang/String;\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const-string v0, ""\n'
  '    return-object v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'contactsCreate()I',
  'c874d46705c43fa492f6aa4b857f80ce88982e0ac3bf1cc256a5df89cb67b3fd',
  '.method public contactsCreate()I\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, -0x1\n'
  '    return v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'contactsGetNumEntries(II)I',
  'b4ea6ebfeef2b0d832368946fcbb480b1092d63da38c4b3ea910b8e915a914ce',
  '.method public contactsGetNumEntries(II)I\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, -0x1\n'
  '    return v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'contactsGetNumRecords()I',
  'b49712c6c1218b7fa666c7226b7eb4e30d884ac26a01defecfe1ec1124d9d106',
  '.method public contactsGetNumRecords()I\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, -0x1\n'
  '    return v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'contactsGetUID(I)I',
  '6c06a156e688c1b9dab234e981454660ea34eb0c36b29183855a7c3b611e322b',
  '.method public contactsGetUID(I)I\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, -0x1\n'
  '    return v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'contactsDelete(I)Z',
  '16a4cf6ead9f42e0699acb57b7ab799bfd04072018eaa3c707d9e23553065992',
  '.method public contactsDelete(I)Z\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, 0x0\n'
  '    return v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'contactsSetField(Ljava/lang/String;III)Z',
  'ae2c53bf6b872b0d97e359c996ce3b35d6289ff02fb9f3355c3bc65962fa74fe',
  '.method public contactsSetField(Ljava/lang/String;III)Z\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, 0x0\n'
  '    return v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'contactsUpdate()Z',
  'cf97b093137ce51290a13a6c0b278decf2840f27f8a1b41e942dcd406c90f7e0',
  '.method public contactsUpdate()Z\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, 0x0\n'
  '    return v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'locationStart()Z',
  '72b8ebfc31f7ec2e3a60d99b1abff33c5d1f71cc015a46348da86de8cbbd0057',
  '.method public locationStart()Z\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, 0x0\n'
  '    return v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'locationStop()Z',
  'ba7a26b8da1b981d5ea6e0fa80ab28e45b52e94ce58c1e743fcb4768d69d2f43',
  '.method public locationStop()Z\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, 0x0\n'
  '    return v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'contactsGetData(II)Landroid/database/Cursor;',
  '05f7b1dc42e578755a226abf3cc7e4f6147281e3fc120e490b9bc48313b6b84e',
  '.method public contactsGetData(II)Landroid/database/Cursor;\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, 0x0\n'
  '    return-object v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayThread.smali',
  'contactsGetField(III)Ljava/lang/String;',
  'afff5fa9ea44d66606830476482ff09d9f5883131d3f41f12736929172c74797',
  '.method public contactsGetField(III)Ljava/lang/String;\n'
  '    # S3CE: private storage and unsupported personal-data services.\n'
  '    .locals 1\n'
  '    const/4 v0, 0x0\n'
  '    return-object v0\n'
  '.end method'),
 ('smali/com/ideaworks3d/airplay/AirplayActivity.smali',
  'backlightOn()V',
  '25877d1e0365fc2a42e043aef525d4e169a10b5a68b567b0bad83b44c6602eb8',
  '.method public backlightOn()V\n'
  '    .locals 0\n'
  '    # S3CE: use the public Window API on the UI thread.\n'
  '    invoke-static {p0}, '
  'Lcom/ideaworks3d/thesims3/CompatActivity;->keepScreenOn(Landroid/app/Activity;)V\n'
  '    return-void\n'
  '.end method')]


def apply(decoded: Path) -> list[str]:
    # Validate every original before writing any file. A changed input or partial
    # manual modification must not silently produce an incompatible build.
    sources: dict[Path, str] = {}
    changed: list[str] = []
    for relative, signature, original_sha, replacement in PATCHES:
        target = decoded / relative
        if target not in sources:
            sources[target] = target.read_text(encoding="utf-8")
        source = sources[target]
        pattern = re.compile(r"^\.method [^\n]* " + re.escape(signature)
                             + r"\n.*?^\.end method", re.M | re.S)
        matches = list(pattern.finditer(source))
        if len(matches) != 1:
            raise ValueError(f"Expected one method {signature}; got {len(matches)}")
        match = matches[0]
        current = match.group()
        if current == replacement:
            continue
        if hashlib.sha256(current.encode()).hexdigest() != original_sha:
            raise ValueError(f"Unexpected method bytes for {signature}; refusing to patch")
        sources[target] = source[:match.start()] + replacement + source[match.end():]
        changed.append(signature)
    for target, source in sources.items():
        target.write_text(source, encoding="utf-8")
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decoded", type=Path)
    args = parser.parse_args()
    for name in apply(args.decoded):
        print(name)
