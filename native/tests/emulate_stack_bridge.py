#!/usr/bin/env python3
"""Execute the compiled production ARM32 stack bridge plus the original gateway.

Requires Unicorn 2.1.4 and Android NDK r28c. pthread APIs and ART's stack-bound
predicate are mocks; the bridge, its inline assembly, and original Airplay
Thumb/ARM gateway execute as real instructions. No Android VM is emulated.
"""
import argparse
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile

import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR,
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
    UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
    UC_ARM_REG_R12, UC_ARM_REG_C1_C0_2, UC_ARM_REG_FPEXC,
    UC_ARM_REG_D8, UC_ARM_REG_D9, UC_ARM_REG_D10, UC_ARM_REG_D11,
    UC_ARM_REG_D12, UC_ARM_REG_D13, UC_ARM_REG_D14, UC_ARM_REG_D15,
    UC_CPU_ARM_CORTEX_A15,
)

LEGACY = 0x10000000
OS_LOW, OS_SIZE = 0xd0000000, 0x100000
GAME_LOW, GAME_SIZE = 0xc0000000, 0x100000
SAVED_OS_SP = OS_LOW + OS_SIZE - 0x2000
GAME_SP = GAME_LOW + GAME_SIZE - 0x1000
STOP = 0x40000000
FIBRE = LEGACY + 0x54b68
LOADER_SLOT = LEGACY + 0x56758
GATEWAY = LEGACY + 0x3c7f0
SOURCE_SHA = 'd93bc59497d377a9524aa8b3fa090aec0e32048bec4bb5e50b757c2f7234befe'
ARGUMENT_REGISTERS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
SAVED_REGISTERS = [UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
                   UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11]

SAVED_FP_REGISTERS = [UC_ARM_REG_D8, UC_ARM_REG_D9, UC_ARM_REG_D10, UC_ARM_REG_D11,
                      UC_ARM_REG_D12, UC_ARM_REG_D13, UC_ARM_REG_D14, UC_ARM_REG_D15]


def u32(vm, address, value=None):
    if value is None:
        return struct.unpack('<I', vm.mem_read(address, 4))[0]
    vm.mem_write(address, struct.pack('<I', value & 0xffffffff))


def elf_header(data):
    assert data[:7] == b'\x7fELF\x01\x01\x01'
    header = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    assert header[2] == 40, 'Expected ARM32 ELF'
    return header


def sections(data):
    header = elf_header(data)
    return [struct.unpack_from('<IIIIIIIIII', data, header[6] + i*header[11])
            for i in range(header[12])]


def symbol_table(data):
    result = {}
    table = sections(data)
    for section in table:
        if section[1] != 2:
            continue
        strings = table[section[6]]
        names = data[strings[4]:strings[4]+strings[5]]
        for at in range(section[4], section[4]+section[5], section[9]):
            name, value, size, info, _, index = struct.unpack_from('<IIIBBH', data, at)
            if name and index:
                name = names[name:names.index(0, name)].decode('ascii')
                result[name] = (value, size, info)
    return result


def load_elf(vm, data, bias, mapped, relocate=False):
    header = elf_header(data)
    assert header[9] == 32
    programs = [struct.unpack_from('<IIIIIIII', data, header[5] + i*32)
                for i in range(header[10])]
    for program in programs:
        if program[0] != 1:
            continue
        start = (bias + program[2]) & ~4095
        end = (bias + program[2] + program[5] + 4095) & ~4095
        for page in range(start, end, 4096):
            if page not in mapped:
                vm.mem_map(page, 4096)
                mapped.add(page)
        vm.mem_write(bias + program[2], data[program[1]:program[1]+program[4]])
    if relocate:
        for section in sections(data):
            if section[1] != 9:
                continue
            for at in range(section[4], section[4]+section[5], section[9]):
                address, info = struct.unpack_from('<II', data, at)
                if info & 255 == 23:
                    u32(vm, bias+address, u32(vm, bias+address) + bias)


def compile_probe(ndk, destination):
    native = Path(__file__).resolve().parents[1]
    compiler = ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi26-clang'
    command = [str(compiler), '-std=gnu11', '-O2', '-mthumb', '-fPIC',
               '-Wall', '-Wextra', '-Werror', '-fstack-protector-strong',
               '-fno-builtin', '-nostdlib', '-static',
               '-Wl,-Ttext=0x20000000,-e,probe_work,--no-undefined',
               str(native/'stack_bridge.c'), str(native/'tests/stack_bridge_probe.c'),
               '-o', str(destination)]
    subprocess.run(command, check=True)
    return destination.read_bytes()


class Scenario:
    def __init__(self, legacy, probe):
        self.vm = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        self.vm.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A15)
        # Android's ARMv7 toolchain may use NEON for local copies.
        self.vm.reg_write(UC_ARM_REG_C1_C0_2,
                          self.vm.reg_read(UC_ARM_REG_C1_C0_2) | 0x00f00000)
        self.vm.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        mapped = set()
        load_elf(self.vm, legacy, LEGACY, mapped, relocate=True)
        load_elf(self.vm, probe, 0, mapped)
        self.symbols = symbol_table(probe)
        self.vm.mem_map(OS_LOW, OS_SIZE)
        self.vm.mem_map(GAME_LOW, GAME_SIZE)
        self.vm.mem_map(STOP, 4096)
        self.vm.mem_write(STOP, b'\x70\x47')
        self.gateway_events = []
        self.gateway_returns = []
        self.checked_entries = []
        self.config_calls = 0
        self.vm.hook_add(UC_HOOK_CODE, self.hook)
        # Execute the original config reader and original setter, rather than
        # inventing their private state. Config callback's mock returns 1.
        self.call(LEGACY+0x3c945, [], SAVED_OS_SP+0x1000)
        assert self.vm.mem_read(FIBRE+0x18, 1) == b'\x01'
        assert u32(self.vm, LOADER_SLOT) == 0
        self.call(LEGACY+0x3c83d, [SAVED_OS_SP], SAVED_OS_SP+0x1000)
        assert self.config_calls == 1 and u32(self.vm, LOADER_SLOT) == SAVED_OS_SP
        assert self.fibre_state() == (0, 0, 0, 1)

    def address(self, name):
        return self.symbols[name][0]

    def value(self, name, value=None):
        return u32(self.vm, self.address(name), value)

    def fibre_state(self):
        return (u32(self.vm, FIBRE+8), self.vm.mem_read(FIBRE+12, 1)[0],
                u32(self.vm, FIBRE+20), self.vm.mem_read(FIBRE+24, 1)[0])

    def hook(self, cpu, address, size, unused):
        if address == STOP:
            cpu.emu_stop()
        elif address == LEGACY+0x2972c:
            cpu.reg_write(UC_ARM_REG_R0, 1)
            self.config_calls += 1
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
        elif address == GATEWAY:
            job = cpu.reg_read(UC_ARM_REG_R0)
            target = cpu.reg_read(UC_ARM_REG_R12)
            assert target == self.address('checked_stack_job'), hex(target)
            assert u32(cpu, job) == self.address('probe_work')
            assert u32(cpu, job+4) == OS_LOW and u32(cpu, job+8) == OS_LOW+OS_SIZE
            self.gateway_events.append((cpu.reg_read(UC_ARM_REG_SP),
                                        cpu.reg_read(UC_ARM_REG_LR), job))
        elif address == (self.address('checked_stack_job') & ~1):
            self.checked_entries.append((cpu.reg_read(UC_ARM_REG_SP),
                                         cpu.reg_read(UC_ARM_REG_R0)))
        elif address == (self.address('__stack_chk_fail') & ~1):
            raise AssertionError('Stack canary failure')
        for entry_sp, continuation, job in self.gateway_events:
            if address == (continuation & ~1):
                observed = (cpu.reg_read(UC_ARM_REG_SP), cpu.reg_read(UC_ARM_REG_LR))
                assert observed == (entry_sp, continuation), (observed, entry_sp, continuation)
                self.gateway_returns.append(observed)

    def call(self, entry, arguments, sp):
        sentinels = {reg:0x44000000+i*0x10101 for i, reg in enumerate(SAVED_REGISTERS)}
        fp_sentinels = {reg:0x1122334455660000+i*0x101 for i, reg in enumerate(SAVED_FP_REGISTERS)}
        for register, value in {**sentinels, **fp_sentinels}.items():
            self.vm.reg_write(register, value)
        for register, value in zip(ARGUMENT_REGISTERS, arguments):
            self.vm.reg_write(register, value)
        self.vm.reg_write(UC_ARM_REG_SP, sp)
        self.vm.reg_write(UC_ARM_REG_LR, STOP|1)
        self.vm.emu_start(entry, 0, count=200000)
        assert self.vm.reg_read(UC_ARM_REG_PC) == STOP, hex(self.vm.reg_read(UC_ARM_REG_PC))
        assert self.vm.reg_read(UC_ARM_REG_SP) == sp, 'Caller SP was not restored'
        for register, value in {**sentinels, **fp_sentinels}.items():
            assert self.vm.reg_read(register) == value, ('callee-saved register', register)
        return self.vm.reg_read(UC_ARM_REG_R0)

    def bridge(self, sp=GAME_SP):
        return self.call(self.address('s3ce_call_on_thread_stack'),
                         [self.address('probe_work'), LOADER_SLOT, GATEWAY, self.address('probe_log')], sp)

    def restored(self, initial_state, expected_loader=SAVED_OS_SP):
        assert self.fibre_state() == initial_state, (self.fibre_state(), initial_state)
        assert u32(self.vm, LOADER_SLOT) == expected_loader
        assert len(self.gateway_events) == len(self.gateway_returns)
        assert self.value('probe_canary_errors') == 0


def run_cases(legacy, probe):
    case = Scenario(legacy, probe)
    case.call(case.address('probe_raw_work'), [], GAME_SP)
    assert case.value('probe_stack_errors') == 1 and case.value('probe_managed_entries') == 0
    assert GAME_LOW <= case.value('probe_raw_sp') < GAME_LOW+GAME_SIZE
    print('PASS raw game-stack managed-call mock rejects entry as StackOverflowError')

    for nested in [False, True]:
        case = Scenario(legacy, probe)
        initial = case.fibre_state()
        case.value('probe_do_nested', int(nested))
        assert case.bridge() == 0
        assert case.value('probe_work_entries') == 1
        assert case.value('probe_managed_entries') == (2 if nested else 1)
        assert case.value('probe_stack_errors') == 0
        assert OS_LOW <= case.value('probe_outer_sp') < SAVED_OS_SP
        assert case.value('probe_outer_flag') == 1
        assert len(case.gateway_events) == 1
        # The compiler may inline the direct OS-stack checked-job branch.
        assert len(case.checked_entries) in ([1, 2] if nested else [1])
        assert case.checked_entries[0][1] == case.gateway_events[0][2]
        if nested:
            assert case.value('probe_nested_entries') == 1 and case.value('probe_nested_status') == 0
            assert OS_LOW <= case.value('probe_nested_sp') < case.value('probe_outer_sp')
            assert case.value('probe_nested_before') == case.value('probe_nested_after')
            assert case.value('probe_nested_flag') == 1
            assert case.value('probe_outer_sp') < SAVED_OS_SP-1024
        case.restored(initial)
        print(f'PASS compiled C/inline ASM -> actual ARM Void gateway -> checked C callback; nested={nested}; r4-r11/d8-d15/SP/return continuation and fibre state restored')

    case = Scenario(legacy, probe)
    case.value('probe_do_nested', 1)
    initial = case.fibre_state()
    assert case.bridge(SAVED_OS_SP-0x8000) == 0
    assert len(case.gateway_events) == 0 and case.value('probe_managed_entries') == 2
    assert case.value('probe_outer_flag') == 0 and case.value('probe_nested_flag') == 0
    case.restored(initial)
    print('PASS already on pthread stack: direct nested callbacks, no saved-SP rewind')

    case = Scenario(legacy, probe)
    u32(case.vm, FIBRE+20, GAME_SP)  # Original near-stack swap detector declines.
    initial = case.fibre_state()
    assert case.bridge() == 0xffffffff
    assert len(case.gateway_events) == 1 and len(case.checked_entries) == 1
    assert GAME_LOW <= case.checked_entries[0][0] < GAME_LOW+GAME_SIZE
    assert case.value('probe_work_entries') == 0 and case.value('probe_managed_entries') == 0
    case.restored(initial)
    print('PASS original IsSwapDisabled refuses switch: checked C callback blocks managed entry')

    for saved in [OS_LOW+4096+65536-8, SAVED_OS_SP+4, OS_LOW+OS_SIZE]:
        case = Scenario(legacy, probe)
        case.call(LEGACY+0x3c83d, [saved], SAVED_OS_SP+0x1000)
        initial = case.fibre_state()
        assert case.bridge() == 0xffffffff
        assert not case.gateway_events and case.value('probe_managed_entries') == 0
        case.restored(initial, expected_loader=saved)
    print('PASS invalid saved SP: guard plus 64 KiB headroom, 8-byte alignment, upper bound')

    case = Scenario(legacy, probe)
    saved = OS_LOW+4096+65536
    case.call(LEGACY+0x3c83d, [saved], SAVED_OS_SP+0x1000)
    initial = case.fibre_state()
    assert case.bridge() == 0 and case.value('probe_managed_entries') == 1
    case.restored(initial, expected_loader=saved)
    print('PASS saved-SP headroom boundary: 64 KiB above the mocked pthread guard')

    case = Scenario(legacy, probe)
    case.value('probe_flip_thread', 1)
    initial = case.fibre_state()
    assert case.bridge() == 0xffffffff
    assert case.value('probe_work_entries') == 0 and case.value('probe_managed_entries') == 0
    case.restored(initial)
    print('PASS callback pthread-identity mismatch blocks managed entry and restores game stack')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Pinned original APK or libairplay.so')
    parser.add_argument('--ndk', type=Path, default=os.environ.get('ANDROID_NDK_HOME'))
    args = parser.parse_args()
    if unicorn.__version__ != '2.1.4':
        parser.error('Install the pinned optional emulator dependency unicorn==2.1.4')
    if not args.ndk:
        parser.error('Provide --ndk or ANDROID_NDK_HOME')
    if zipfile.is_zipfile(args.source):
        with zipfile.ZipFile(args.source) as source:
            legacy = source.read('lib/armeabi/libairplay.so')
    else:
        legacy = args.source.read_bytes()
    assert hashlib.sha256(legacy).hexdigest() == SOURCE_SHA
    assert legacy[0x3c7f0:0x3c7fc] == bytes.fromhex('00402de997ffffeb0040bde8')
    with tempfile.TemporaryDirectory(prefix='s3ce-stack-emulation-') as temporary:
        probe = compile_probe(args.ndk, Path(temporary)/'probe.elf')
        assert elf_header(probe)[1] == 2, 'Probe must be a statically linked ET_EXEC'
        run_cases(legacy, probe)


if __name__ == '__main__':
    main()
