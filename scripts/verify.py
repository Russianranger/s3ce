#!/usr/bin/env python3
"""Validate packaging invariants; this does not establish runtime gameplay."""
import hashlib
from pathlib import Path
import struct
import sys
import zipfile

def verify(original, candidate):
    with zipfile.ZipFile(original) as before, zipfile.ZipFile(candidate) as after:
        assert after.testzip() is None, 'APK ZIP CRC failure'
        assert {'classes.dex', 'classes2.dex', 'assets/compat/libairplay-legacy.so',
                'lib/armeabi-v7a/libairplay.so'} <= set(after.namelist())
        assert not any(n.startswith('lib/armeabi/') for n in after.namelist())
        assets = [n for n in before.namelist() if n.startswith('assets/')]
        for name in assets:
            assert hashlib.sha256(before.read(name)).digest() == hashlib.sha256(after.read(name)).digest(), name
            assert after.getinfo(name).compress_type == zipfile.ZIP_STORED, name + ': must support AssetManager.openFd'
        assert before.read('lib/armeabi/libairplay.so') == after.read('assets/compat/libairplay-legacy.so')
        shim = after.read('lib/armeabi-v7a/libairplay.so')
        assert shim[:6] == b'\x7fELF\x01\x01'
        assert struct.unpack_from('<H', shim, 18)[0] == 40, 'Expected ARM ELF'
        phoff = struct.unpack_from('<I', shim, 28)[0]
        phentsize, phnum = struct.unpack_from('<HH', shim, 42)
        for i in range(phnum):
            kind, offset, _, _, size, _, flags, align = struct.unpack_from('<8I', shim, phoff + i * phentsize)
            if kind == 1: assert flags & 3 != 3, 'Shim has writable executable segment'
            if kind == 0x6474e551: assert flags & 1 == 0, 'Executable stack'
            if kind == 2:
                entries = [struct.unpack_from('<iI', shim, p) for p in range(offset, offset + size, 8)]
                assert not any(tag == 22 or (tag == 30 and value & 4) for tag, value in entries), 'Shim text relocations'
        print('PASS: ZIP CRC,', len(assets), 'unchanged/stored assets, legacy ELF identity, ARM32 shim, NX stack, no W+X load segments/text relocations.')

if __name__ == '__main__':
    verify(Path(sys.argv[1]), Path(sys.argv[2]))
