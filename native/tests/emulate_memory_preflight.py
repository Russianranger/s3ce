#!/usr/bin/env python3
"""Run the original RAM reader/property/preflight Thumb instructions with mock /proc IO.
Requires the optional pinned Unicorn dependency; no Android system is emulated.
"""
import argparse
import hashlib
import re
import zipfile
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
from emulate_gl_start import machine, cstring, word, BASE, AUX, STACK, ELF_SHA


def run(data, free_kib):
    vm = machine(data)
    stop = AUX + 0xff0
    vm.mem_write(stop, b'\x70\x47')
    lines = [b'MemTotal: 16777216 kB\n', f'MemFree: {free_kib} kB\n'.encode()]
    next_line, result = [0], {}
    # Only libc/config/unrelated startup boundaries are mocked. The original
    # get_mem_info, DeviceGetInt(6), comparison, and failing branch execute.
    mocks = {0x9f94,0x9ca0,0x9f4c,0x9fd0,0x366e8,0x2ca74,0x169e0,0x18a2c,0x1b140,0x297a8,0x29768}
    for address in mocks:
        vm.mem_write(BASE+address, b'\x1e\xff\x2f\xe1' if address < 0x10000 else b'\x70\x47')

    def hook(cpu, address, size, unused):
        offset = address-BASE
        if offset == 0x9f94:
            assert cstring(cpu,cpu.reg_read(UC_ARM_REG_R0)) == '/proc/meminfo'
            cpu.reg_write(UC_ARM_REG_R0, 0xabcdef)
        elif offset == 0x9ca0:
            buffer = cpu.reg_read(UC_ARM_REG_R0)
            if next_line[0] < len(lines):
                cpu.mem_write(buffer, lines[next_line[0]]+b'\0')
                next_line[0] += 1
            else:
                cpu.reg_write(UC_ARM_REG_R0, 0)
        elif offset == 0x9f4c:
            text = cstring(cpu,cpu.reg_read(UC_ARM_REG_R0))
            key = cstring(cpu,cpu.reg_read(UC_ARM_REG_R1)).split(':')[0]
            match = re.match(key+r':\s+(\d+)',text)
            if match:
                word(cpu,cpu.reg_read(UC_ARM_REG_R2),int(match[1]))
            cpu.reg_write(UC_ARM_REG_R0, bool(match))
        elif offset in mocks:
            cpu.reg_write(UC_ARM_REG_R0,0)
        elif offset == 0x190dc:
            result['raw_bytes'] = cpu.reg_read(UC_ARM_REG_R0)
        elif offset == 0x190e4:
            result['required'] = cpu.reg_read(UC_ARM_REG_R3)
        elif offset in [0x190e6,0x1911a]:
            result['accepted'] = offset == 0x190e6
            cpu.emu_stop()
        elif address == stop:
            cpu.emu_stop()
    vm.hook_add(UC_HOOK_CODE,hook)
    vm.reg_write(UC_ARM_REG_SP,STACK+0x8000)
    vm.reg_write(UC_ARM_REG_LR,stop|1)
    vm.reg_write(UC_ARM_REG_R0,0)
    vm.emu_start(BASE+0x19081,0,count=10000)
    assert result['required'] == 65536
    raw = result['raw_bytes']
    signed = raw if raw < 0x80000000 else raw-0x100000000
    assert raw == (free_kib*1024)&0xffffffff
    assert result['accepted'] == (signed >= 65536)
    print(f'PASS original Thumb MemFree={free_kib}KiB -> signed bytes={signed}; startup={"accepted" if result["accepted"] else "pre-allocation memory error"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,help='Pinned original APK or libairplay.so')
    args = parser.parse_args()
    if zipfile.is_zipfile(args.source):
        with zipfile.ZipFile(args.source) as apk:
            data = apk.read('lib/armeabi/libairplay.so')
    else:
        data = args.source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ELF_SHA
    for value in [32,64,1048576,2097152,3145728,4194304,5242880,7340032,16777216]:
        run(data,value)
