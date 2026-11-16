#!/usr/bin/env python3
"""Read the original Android CE relationship graph; never modify an APK or save.

This version-specific reader supplements the recorded original-ARM loader,
selector and transition experiments in docs/RELATIONSHIP_MECHANICS.md.
"""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import struct
import zipfile

APK_SHA = 'a759fb156efb526149e3c0e3a9ca3bba4d5646aff4198ae8946dbc7947c7f5eb'
RESOURCE_SHA = '778c385d6ee62e48bacfea06d5a61b71d1caced5a68b45edaf3cfdb1801511f4'
STATES = ('Stranger', 'Acquaintance', 'Disliked', 'Enemy', 'Nemesis',
          'Friend', 'Good Friend', 'Best Friend', 'Budding Romance', 'Date',
          'Partner', 'Fiancee', 'Spouse', 'Ex-Spouse', 'Ex')


def relationship_resource(apk):
    if hashlib.sha256(apk.read_bytes()).hexdigest() != APK_SHA:
        raise ValueError('Expected the exact signed 0.1.15 Flip3 APK')
    with zipfile.ZipFile(apk) as archive:
        dz = archive.read('assets/res.dz.jpg')
    count, directories = struct.unpack_from('<HH', dz, 4)
    cursor, names = 8, []
    for _ in range(count + directories):
        end = dz.index(0, cursor)
        names.append(dz[cursor:end].decode('utf-8'))
        cursor = end + 1
    table = cursor + count * 6 + 4
    entry = 6
    if names[entry + 1] != 'simsdata.bin':
        raise ValueError('Unexpected resource index')
    offset, size, duplicate, flags = struct.unpack_from('<4I', dz, table + 16 * entry)
    end = struct.unpack_from('<I', dz, table + 16 * (entry + 1))[0]
    data = dz[offset:end]
    if flags & 0x200:
        data = lzma.decompress(data, format=lzma.FORMAT_ALONE)
    if hashlib.sha256(data).hexdigest() != RESOURCE_SHA:
        raise ValueError('Unexpected original relationship tuning')
    return data


def read_graph(data):
    # Original loader cf0bc and an independent format parse agree on this span.
    if data[0x57d:0x57f] != bytes((2, 15)):
        raise ValueError('Unexpected score-channel or relationship-state count')
    cursor, rows = 0x57f, []
    for state, name in enumerate(STATES):
        name_id, flags, category_id, notification_id, count = struct.unpack_from('>HBHHB', data, cursor)
        start = cursor
        cursor += 8
        edges = []
        for _ in range(count):
            target, channel, threshold = struct.unpack_from('>BBh', data, cursor)
            if target >= len(STATES) or channel >= 2:
                raise ValueError('Invalid relationship transition')
            edges.append({'target': target, 'target_name': STATES[target],
                          'channel': channel, 'threshold': threshold})
            cursor += 4
        rows.append({'state': state, 'name': name, 'record_offset': hex(start),
                     'flags': flags, 'edges': edges})
    if cursor != 0x65f:
        raise ValueError('Unexpected relationship section extent')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, required=True)
    args = parser.parse_args()
    rows = read_graph(relationship_resource(args.apk))
    print(json.dumps({'apk_sha256': APK_SHA, 'resource_sha256': RESOURCE_SHA,
                      'scope': 'Read-only original tuning; no Android gameplay or patch',
                      'states': rows}, indent=2))


if __name__ == '__main__':
    main()
