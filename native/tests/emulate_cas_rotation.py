#!/usr/bin/env python3
"""Execute the source game's CAS rotation entry and its real soft-float helpers.

Requires the optional pinned Unicorn dependency and the user-supplied unpacked
S3E file. No game instructions or arithmetic results are mocked. This verifies
the isolated rotation consumer, not device delivery of a drag to that consumer.

Example (from the repository):
  PYTHONPATH=/path/to/unicorn python native/tests/emulate_cas_rotation.py \
      '/path/to/The Sims 3.s3e.unpacked'
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R4,
    UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8,
    UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_SP,
    UC_ARM_REG_LR, UC_ARM_REG_PC,
)

SOURCE_SHA = '8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a'
CODE_OFFSET, CODE_EXTENT = 0xd2a0, 0x166ad8
CODE_BASES = (0x4a000000, 0xc0cb8000)
ENTRY = 0x11b644
OBJECT, ENGINE = 0xd0000000, 0xd0001000
EVENT, WRAPPER, ARRAY = 0xd0002000, 0xd0002100, 0xd0002200
INITIAL_SP, RETURN_PC = 0xe0008000, 0xe0010000
SAVED = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
         UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11)
HELPERS = {
    0x126df8: 'viewport_width', 0x1495cc: 'int_to_float',
    0x14923c: 'float_divide', 0x14973c: 'float_multiply',
    0x149118: 'float_add', 0xc4714: 'float_clamp',
}


def run_case(code, base):
    vm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    # The real loader separates data/BSS from code. This consumer reaches only
    # code/constant bytes below CODE_EXTENT; no preferred-VMA globals are mapped.
    vm.mem_map(base, (len(code) + 4095) & ~4095)
    vm.mem_write(base, code)
    vm.mem_map(OBJECT, 0x10000)
    vm.mem_map(0xe0000000, 0x20000)
    vm.mem_write(RETURN_PC, bytes.fromhex('1eff2fe1'))  # ARM BX LR

    def word(address, value):
        vm.mem_write(address, struct.pack('<I', value & 0xffffffff))

    # Handler ABI: (SceneMenu*, eventKind=5, eventObject*). The event array
    # stores current X, previous X and delta time in milliseconds.
    word(OBJECT + 0x20, ENGINE)
    word(ENGINE + 8, 1920)
    word(ENGINE + 0xc, 1080)
    word(ENGINE + 0x10, 0)
    word(EVENT + 0xc, WRAPPER)
    word(WRAPPER + 8, ARRAY)
    word(ARRAY + 4, 1520)
    word(ARRAY + 0x14, 1500)
    word(ARRAY + 0x24, 16)
    for register, value in ((UC_ARM_REG_R0, OBJECT), (UC_ARM_REG_R1, 5),
                            (UC_ARM_REG_R2, EVENT), (UC_ARM_REG_SP, INITIAL_SP),
                            (UC_ARM_REG_LR, RETURN_PC)):
        vm.reg_write(register, value)
    saved = {register: 0x90000400 + index * 0x100
             for index, register in enumerate(SAVED)}
    for register, value in saved.items():
        vm.reg_write(register, value)
    visits, branch_seen = [], []

    def observe(cpu, address, _size, _user_data):
        if address == RETURN_PC:
            cpu.emu_stop()
            return
        offset = address - base
        if offset == 0x11c244:
            branch_seen.append(offset)
        if offset in HELPERS:
            visits.append({'offset': hex(offset), 'name': HELPERS[offset],
                           'r0': hex(cpu.reg_read(UC_ARM_REG_R0)),
                           'r1': hex(cpu.reg_read(UC_ARM_REG_R1))})

    vm.hook_add(UC_HOOK_CODE, observe)
    vm.emu_start(base + ENTRY, 0, count=1000000)
    assert vm.reg_read(UC_ARM_REG_PC) == RETURN_PC, 'Handler did not return'
    assert vm.reg_read(UC_ARM_REG_SP) == INITIAL_SP, 'SP was not restored'
    assert branch_seen, 'Single-drag branch was not entered'
    for register, value in saved.items():
        assert vm.reg_read(register) == value, 'Callee-saved register changed'
    angle, inertia, timer = struct.unpack('<ffI', vm.mem_read(OBJECT + 0xe20, 12))
    assert (angle, inertia, timer) == (-3.75, -0.234375, 1000)
    assert set(HELPERS) <= {int(item['offset'], 16) for item in visits}
    return {'code_base': hex(base), 'object': hex(OBJECT), 'delta_x': 20,
            'width': 1920, 'angle': angle, 'inertia': inertia, 'timer': timer,
            'sp_and_callee_saved_preserved': True, 'actual_helper_calls': visits}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Pinned unpacked source S3E')
    parser.add_argument('--json', action='store_true', help='Print full helper-call evidence')
    args = parser.parse_args()
    if unicorn.__version__ != '2.1.4':
        parser.error('Install the pinned optional dependency unicorn==2.1.4')
    data = args.source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA, 'Unexpected source SHA256'
    assert data[:4] == b'XE3U', 'Unexpected unpacked image magic'
    assert struct.unpack_from('<I', data, 0x14)[0] == CODE_OFFSET
    assert struct.unpack_from('<I', data, 0x44)[0] == CODE_EXTENT
    assert CODE_OFFSET + CODE_EXTENT <= len(data)
    code = data[CODE_OFFSET:CODE_OFFSET + CODE_EXTENT]
    results = [run_case(code, base) for base in CODE_BASES]
    if args.json:
        print(json.dumps({'source_sha256': SOURCE_SHA, 'results': results}, indent=2))
    for result in results:
        print(f'PASS original CAS rotation entry {result["code_base"]}: 20px/1920 '
              '-> angle=-3.75, inertia=-0.234375, timer=1000; '
              'real math helpers, high object, SP/r4-r11 preserved; no stubs')


if __name__ == '__main__':
    main()
