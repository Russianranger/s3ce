#!/usr/bin/env python3
"""Execute the shipped implicit TriangleStripArray parser at low and high VMAs.

Original ARM parser, byte swaps, constructors, vectors, COW assignment,
refcounts, destructor and length-copy instructions execute. Only typed reads
and allocator/free boundaries are modeled. This is not a GPU test.
The source binary is user-supplied and SHA-256 pinned. No asset, JSON file,
or proprietary fixture is stored in this test; the original 22-byte type11
object body and proposed 29-byte equivalent are embedded below.
Run: python emulate_ui_strip_parser.py --source /path/to/game.unpacked
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True,
                    help='Original unpacked S3E game image (SHA-256 pinned)')
args = parser.parse_args()
IMAGE = args.source.read_bytes()
SOURCE_SHA = '8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a'
assert hashlib.sha256(IMAGE).hexdigest() == SOURCE_SHA
# Original UI atlas sprite TriangleStripArray (type11, object5). The first
# twelve bytes are its unchanged Object3D header. Original encoding01 stores
# first index as u8, then one little endian strip count and length4.
RAW = bytes.fromhex('00000000000000000000000001000100000004000000')
assert len(RAW) == 22
# Equivalent explicit encoding81: four u8 indices, one length4 strip.
EXPLICIT_RAW = RAW[:12] + b'\x81' + struct.pack('<I', 4) + bytes(range(4)) + struct.pack('<II', 1, 4)
PREFERRED = 0x4a000000
CODE_OFFSET, CODE_EXTENT, IMAGE_EXTENT = 0xd2a0, 0x166ad8, 0x169010
CODE = IMAGE[CODE_OFFSET:CODE_OFFSET + CODE_EXTENT]
INITIAL_DATA = IMAGE[CODE_OFFSET + CODE_EXTENT:CODE_OFFSET + IMAGE_EXTENT]
# Exact instruction pins. The SHA additionally pins the entire source image.
PINS = {
    0x9c52c: '6000a0e3',   # mov r0,#0x60
    0x9c624: '8c008de2',   # add r0,sp,#0x8c (implicit byte first index)
    0x9c634: 'b10400eb',   # bl9d900
    0x9c838: '8c008de2',   # add r0,sp,#0x8c (strip count)
    0x9c8b0: '051180e7',   # str r1,[r0,r5,lsl#2] (strip length)
    0x9c8c8: 'c00400eb',   # bl9dbd0
    0x9d900: '281080e5',   # str r1,[r0,#0x28]
    0x9dce8: '5d9702eb',   # bl143a64 (drop temporary COW reference)
    0x9dd2c: 'b220e1e1',   # strh r2,[r1,#2]! (length to ushort)
    0xa573c: '0810a0e3',   # mov r1,#8 (primitive)
}
for off, expected in PINS.items():
    assert CODE[off:off+4].hex() == expected, f'instruction pin {off:x}'
# These are precisely the literal/vtable pointer reads reached in the original
# low-VMA execution, collected with a memory-read hook. Do not scan/rewrite all
# words in the preferred range: ARM conditional instructions share that prefix.
RELOCATIONS = {
    0x9cd34: 0x1608c0, 0x9cd38: 0x1620fc,
    0x9d8f8: 0x16214c, 0x9d8fc: 0x1608e8,
    0x9dd68: 0x16214c, 0x9dd6c: 0x1608e8, 0x9e194: 0x15fe54,
    0xa5750: 0x160320, 0xa9cb0: 0x1605a4, 0xa9cb4: 0x161f6c,
    0xb2880: 0x160ef4, 0xb28b8: 0x160ef4, 0xb73a0: 0x16234c,
    0x143504: 0x1620fc, 0x143508: 0x1608e8, 0x1436a4: 0x1620fc,
    0x143a48: 0x16214c, 0x143b28: 0x16214c,
    0x1608ec: 0xaf304, 0x1608f0: 0xb283c, 0x1608f4: 0xb285c,
    0x162118: 0x14332c, 0x162168: 0x14396c,
}
for off, target in RELOCATIONS.items():
    assert struct.unpack_from('<I', CODE, off)[0] == PREFERRED + target


def run(code_base, data_base, heap_base, stack_base, raw=RAW):
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for start, size in [(code_base, 0x200000), (data_base, 0x20000),
                        (heap_base, 0x100000), (stack_base, 0x10000)]:
        u.mem_map(start, size)
    u.mem_write(code_base, CODE)
    u.mem_write(data_base, INITIAL_DATA)
    for off, target in RELOCATIONS.items():
        relocated = (code_base + target if target < CODE_EXTENT else
                     data_base + target - CODE_EXTENT)
        u.mem_write(code_base + off, struct.pack('<I', relocated))
    stack = stack_base + 0x8000
    cursor, position = heap_base, 0
    reads, seen = [], set()
    allocations = []
    alloc = {0x132cac, 0x132ca4, 0x139368, 0x13c80c}
    free = {0x132c9c, 0x132c94, 0x135910}

    def reg(number):
        return u.reg_read(number)

    def word(address):
        return struct.unpack('<I', u.mem_read(address, 4))[0]

    def ret(value=None):
        if value is not None:
            u.reg_write(UC_ARM_REG_R0, value)
        u.reg_write(UC_ARM_REG_PC, reg(UC_ARM_REG_LR))

    def hook(_u, pc, _size, _arg):
        nonlocal cursor, position
        off = pc - code_base
        seen.add(off)
        if off == 0x9c8d8:
            u.emu_stop()
        elif off in alloc:
            size = reg(UC_ARM_REG_R0)
            assert 0 < size < 0x10000, f'unexpected alloc {size}'
            address = cursor
            cursor += (size + 15) & ~15
            assert cursor < heap_base + 0x100000
            # Poison catches missed initialization in the original constructors.
            u.mem_write(address, b'\xa5' * ((size + 15) & ~15))
            allocations.append((off, address, size))
            ret(address)
        elif off in free:
            ret()
        elif off in (0xb1990, 0xb1a44):
            assert reg(UC_ARM_REG_R0) == stack + 0x8c
            size = 1 if off == 0xb1990 else 4
            assert position + size <= len(raw), 'read beyond raw M3G object'
            chunk = raw[position:position+size]
            # readInt returns stream order (big endian); the actual parser's
            # byte-swap decodes the little endian M3G payload afterwards.
            result = int.from_bytes(chunk, 'big')
            reads.append({'offset': position, 'size': size,
                          'bytes': chunk.hex(), 'reader_value': result})
            position += size
            ret(result)

    u.hook_add(UC_HOOK_CODE, hook)
    u.reg_write(UC_ARM_REG_SP, stack)
    u.emu_start(code_base + 0x9c52c, 0, count=100000)
    assert reg(UC_ARM_REG_PC) == code_base + 0x9c8d8, 'budget exhausted'
    assert position == len(raw), (position, len(raw))
    obj = reg(UC_ARM_REG_R6)
    first = word(obj + 0x28)
    index_count = word(obj + 0x38)
    index_record = word(obj + 0x3c)
    strip_count = word(obj + 0x4c)
    strip_record = word(obj + 0x50)
    strip_data = word(strip_record + 8)
    lengths = list(struct.unpack('<' + 'H' * strip_count,
                               u.mem_read(strip_data, 2 * strip_count)))
    primitive = word(obj + 0x5c)
    explicit = raw[12] == 0x81
    if explicit:
        assert (first, index_count, strip_count, lengths, primitive) == (0xffffffff, 4, 1, [4], 8)
        index_data = word(index_record + 8)
        indices = list(struct.unpack('<4H', u.mem_read(index_data, 8)))
        assert indices == [0, 1, 2, 3]
        assert word(index_record + 4) == 1
    else:
        assert (first, index_count, index_record, strip_count, lengths, primitive) == (0, 0, 0, 1, [4], 8)
        indices = []
    assert word(strip_record + 4) == 1, 'COW retained reference count'
    assert word(strip_record + 0xc) == 2, 'ushort element size'
    assert word(strip_record + 0x10) == 1, 'COW element count'
    # Derived from the parsed implicit range; these are not stored TSA fields.
    low, high = ((min(indices), max(indices)) if explicit else (first, first + sum(lengths) - 1))
    assert (low, high) == (0, 3)
    for off in (0xa5728, 0x9e150, 0xa125c, (0x9d77c if explicit else 0x9d900), 0x14343c,
                0x9dbd0, 0x9dd2c, 0x143a64):
        assert off in seen, f'original path not executed: {off:x}'
    assert reg(UC_ARM_REG_SP) == stack
    return {
        'encoding': hex(raw[12]), 'raw_hex': raw.hex(),
        'code_base': hex(code_base), 'data_base': hex(data_base),
        'heap_base': hex(heap_base), 'stack_base': hex(stack_base),
        'consumed_bytes': position, 'first_index_at_28': first,
        'explicit_index_count_at_38': index_count,
        'explicit_index_record_nonnull_at_3c': bool(index_record),
        'ushort_explicit_indices': indices,
        'strip_count_at_4c': strip_count, 'ushort_strip_lengths': lengths,
        'primitive_at_5c': primitive, 'derived_low': low, 'derived_high': high,
        'cow_refcount': word(strip_record + 4),
        'stack_restored': True, 'typed_reads': reads,
    }


if __name__ == '__main__':
    results = [run(*layout, raw=raw) for raw in (RAW, EXPLICIT_RAW)
               for layout in ((0x4a000000, 0x68000000, 0x60000000, 0x70000000),
                              (0xc0cb8000, 0xd1000000, 0xbfc00000, 0xbff00000))]
    print(json.dumps({
        'game_sha256': SOURCE_SHA,
        'object_type': 11, 'original_raw_hex': RAW.hex(),
        'original_parser_offsets': '0x9c52c..0x9c8d8',
        'mocked_boundaries': ['typed byte/int reads', 'allocator/free'],
        'exact_relocated_pointer_count': len(RELOCATIONS),
        'layouts': results,
    }, indent=2))
