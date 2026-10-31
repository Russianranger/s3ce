#!/usr/bin/env python3
"""Execute compiled production callback proxies through the real legacy/game code.

Uses the user-supplied original runtime and unpacked game. No game code is bundled.
The real registry, generated generic proxy, nested callback gateway, game pointer
adapters, double-buffer drain and gesture decisions execute as ARM instructions.
External allocation/locks/timers and post-transition UI effects are modeled.
"""
import argparse
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile

from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_PC, UC_ARM_REG_LR,
    UC_ARM_REG_R9, UC_ARM_REG_C1_C0_2, UC_ARM_REG_FPEXC,
    UC_CPU_ARM_CORTEX_A15)
from emulate_gl_start import BASE, AUX, STACK, ELF_SHA, word
from emulate_pointer_queue import QueueProof
from emulate_stack_bridge import load_elf, symbol_table
from game_pointer_fixture import GamePointerFixture


def compile_probe(ndk, output, text_address=0x21000000):
    native = Path(__file__).resolve().parents[1]
    compiler = ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi26-clang'
    subprocess.run([str(compiler), '-std=gnu11', '-O2', '-mthumb', '-fPIC',
        '-Wall', '-Wextra', '-Werror', '-fstack-protector-strong', '-fno-builtin',
        '-nostdlib', '-static', f'-Wl,-Ttext={text_address:#x},-e,probe_bind,--no-undefined',
        str(native/'pointer_callbacks.c'), str(native/'tests/pointer_callbacks_probe.c'),
        '-o', str(output)], check=True)
    return output.read_bytes()


class ProxyProof(QueueProof):
    def __init__(self, legacy, probe, game_source, high=True, observe=True):
        self.symbols = None
        self.cpu_configured = False
        self.time_ms = 0
        self.fail_allocations = 0
        self.dynamic_calls, self.proxy_entries, self.game_gateways = [], [], []
        super().__init__(legacy, 1, UC_CPU_ARM_CORTEX_A15)
        load_elf(self.vm, probe, 0, set())
        self.symbols = symbol_table(probe)
        self.call(self.address('probe_bind'), (BASE,))
        self.call(BASE + 0x3c8b5, (AUX + 0x2000,))  # Original dynamic arena setup.
        for old, name, fingerprint in (
            (0x3752c, 's3ce_pointer_register_observed', '10b582b0041c0092'),
            (0x3766c, 's3ce_pointer_unregister_observed', '00b583b00b1c0021')):
            assert bytes(self.vm.mem_read(BASE + old, 8)) == bytes.fromhex(fingerprint)
            if observe:
                self.vm.mem_write(BASE + old, b'\xdf\xf8\x00\xf0'
                    + struct.pack('<I', self.address(name)))
        code, heap, stack, data = ((0xc0cb8000, 0xbfc00000, 0xbff00000, 0xd1000000)
            if high else (0x4a000000, 0x60000000, 0x70000000, 0x68000000))
        self.vm.mem_map(stack, 0x10000)
        self.game_sp = stack + 0xf000
        self.game = GamePointerFixture(self.vm, game_source, code, heap, data)
        self.cookie = 0xf1234567
        self.actual_callbacks = {0: self.game.button_address, 1: self.game.move_address}

    def address(self, name):
        return self.symbols[name][0]

    def call(self, entry, arguments=(), sp=None):
        if not self.cpu_configured:
            self.vm.reg_write(UC_ARM_REG_C1_C0_2,
                self.vm.reg_read(UC_ARM_REG_C1_C0_2) | 0x00f00000)
            self.vm.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
            self.cpu_configured = True
        return super().call(entry, arguments, sp)

    def hook(self, cpu, address, size, unused):
        if address == BASE + 0x35ff0 and self.fail_allocations:
            self.fail_allocations -= 1
            cpu.reg_write(UC_ARM_REG_R0, 0)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
            return
        if address == BASE + 0x3d654:
            self.time_ms += 16
            cpu.reg_write(UC_ARM_REG_R0, self.time_ms)
            cpu.reg_write(UC_ARM_REG_R1, 0)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
            return
        if address == BASE + 0x169c8:  # Platform cache-maintenance syscall boundary.
            cpu.reg_write(UC_ARM_REG_R0, 0)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
            return
        if address == BASE + 0x3c9a0:
            assert cpu.reg_read(UC_ARM_REG_R1) == 4
            assert cpu.reg_read(UC_ARM_REG_R2) == 0  # Never FAST.
            self.dynamic_calls.append(cpu.reg_read(UC_ARM_REG_R0))
        if self.symbols:
            if address == (self.address('probe_invoke') & ~1):
                sp = cpu.reg_read(UC_ARM_REG_SP)
                assert self.os_sp - 0x4000 < sp < self.os_sp
                self.proxy_entries.append((cpu.reg_read(UC_ARM_REG_R0),
                    cpu.reg_read(UC_ARM_REG_R1), cpu.reg_read(UC_ARM_REG_R2), sp))
            if address == (self.address('__stack_chk_fail') & ~1):
                raise AssertionError('Compiled proxy stack canary failure')
        if address == BASE + 0x3c558:
            self.game_gateways.append((cpu.reg_read(UC_ARM_REG_R0),
                cpu.reg_read(UC_ARM_REG_R1), cpu.reg_read(UC_ARM_REG_R2)))
        super().hook(cpu, address, size, unused)

    def register(self, kind, callback=None, cookie=None):
        return self.api(0x3752c, (kind, callback or self.actual_callbacks[kind],
            self.cookie if cookie is None else cookie))

    def unregister(self, kind, callback=None):
        return self.api(0x3766c, (kind, callback or self.actual_callbacks[kind]))


def gesture(case, expected_proxy):
    assert case.register(0) == 0 and case.register(1) == 0
    assert case.register(1, cookie=0x98765432) == 1  # Original dedup ignores cookie.
    assert len(case.dynamic_calls) == (2 if expected_proxy else 0)
    initial = case.fibre_state()
    for native_kind, x, y, state in ((4, 500, 600, 1), (6, 505, 600, 1),
            (6, 520, 600, 3), (6, 900, 630, 3), (5, 900, 630, 0)):
        case.motion(0, native_kind, x, y)
        case.dispatch()  # Actual DeviceYield(0) and original callback chain.
        assert case.game.snapshot()['counts'] in ((1, 0), (0, 1))
        r9 = case.vm.reg_read(UC_ARM_REG_R9)
        case.game.drain(case.game_sp, case.stop | 1)
        assert case.vm.reg_read(UC_ARM_REG_R9) == r9
        assert case.game.snapshot()['counts'] == (0, 0)
        assert case.game.snapshot()['state'] == state
        assert case.fibre_state() == initial
    assert case.game.snapshot()['current'] == (900, 630)
    assert case.game.transitions == [(0, 1), (1, 3), (3, 0)]
    assert len(case.game.received) == 5
    assert all(row[2] == case.cookie and row[3] == 0
               and case.game_sp - 0x1000 < row[4] < case.game_sp
               for row in case.game.received)
    assert len(case.proxy_entries) == (5 if expected_proxy else 0)
    assert len(case.game_gateways) == (10 if expected_proxy else 5)
    assert case.unregister(1) == 0 and case.unregister(1) == 1
    assert case.unregister(0) == 0


def run(legacy, probe, game_source):
    for high in (False, True):
        for observed in (False, True):
            case = ProxyProof(legacy, probe, game_source, high, observed)
            gesture(case, observed)
            print(f'PASS compiled proxy={observed} highAddresses={high}: original registry '
                'and dynamic generic stub -> original callback gateway -> compiled C '
                '-> nested gateway -> actual split-data game callbacks/queue/drain/FSM; '
                'states1/1/3/3/0, cookie/R9/SP/fibre state unchanged')
    case = ProxyProof(legacy, probe, game_source)
    word(case.vm, case.address('probe_generation_failure'), 1)
    assert case.register(0) == 0
    word(case.vm, case.address('probe_generation_failure'), 0)
    assert case.register(0, cookie=0x87654321) == 1
    assert not case.dynamic_calls
    case.motion(0, 4, 500, 600)
    case.dispatch()
    assert len(case.game.received) == 1 and not case.proxy_entries
    assert case.game.received[0][2] == case.cookie
    assert case.unregister(0) == 0
    print('PASS real original registry: permanent generation-failure pass-through '
          'preserves changed-cookie duplicate rejection and unregister')
    case = ProxyProof(legacy, probe, game_source)
    original = [word(case.vm, case.address('probe_originals') + 4 * i) for i in range(17)]
    assert case.register(0, original[0]) == 0
    assert case.register(0, original[0], 0x87654321) == 1
    assert case.register(1, original[0], 0x87654321) == 0
    assert case.register(0, original[1]) == 0
    assert case.unregister(0, original[0]) == 0
    case.motion(0, 4, 500, 600)
    case.dispatch()
    assert word(case.vm, case.address('probe_original_calls')) == 0
    assert word(case.vm, case.address('probe_original_calls') + 4) == 1
    print('PASS real registry duplicate-cookie policy, same-fn/different-event, '
          'multiple callbacks and selective unregister')
    case = ProxyProof(legacy, probe, game_source)
    case.fail_allocations = 1
    assert case.register(1) == 1
    assert case.register(1) == 0
    assert len(case.dynamic_calls) == 1
    assert case.unregister(1) == 0
    print('PASS real original allocation-failed first registration -> successful '
          'retry preserves one generated identity')
    case = ProxyProof(legacy, probe, game_source)
    original = [word(case.vm, case.address('probe_originals') + 4 * i) for i in range(17)]
    for callback in original:
        assert case.register(0, callback) == 0
    assert len(case.dynamic_calls) == 16
    assert case.register(0, original[-1], 0x87654321) == 1
    case.motion(0, 4, 500, 600)
    case.dispatch()
    assert [word(case.vm, case.address('probe_original_calls') + 4 * i)
            for i in range(17)] == [1] * 17
    assert len(case.proxy_entries) == 16
    assert case.unregister(0, original[-1]) == 0
    print('PASS real original >10-callback Notify path and sixteen-slot bound: '
          'seventeenth callback passes through once with original duplicate/unregister semantics')
    case = ProxyProof(legacy, probe, game_source)
    for address, target in ((AUX + 0x600, 0x3752c), (AUX + 0x620, 0x3766c)):
        case.vm.mem_write(address, struct.pack('<IIII', 0xe59fc000, 0xe59ff000,
            BASE + target + 1, BASE + 0x3c808))
    word(case.vm, case.address('probe_register_api'), AUX + 0x600)
    word(case.vm, case.address('probe_unregister_api'), AUX + 0x620)
    assert case.register(1, case.address('probe_reentrant')) == 0
    case.motion(0, 4, 500, 600)
    case.motion(0, 6, 520, 600)
    case.dispatch()
    assert len(case.proxy_entries) == 1
    case.motion(0, 6, 900, 630)
    case.dispatch()
    assert len(case.proxy_entries) == 2
    assert word(case.vm, case.address('probe_original_calls') + 4) == 1
    assert case.unregister(1, case.address('probe_reentrant')) == 1
    print('PASS compiled callback reenters actual generic API gateways to '
          'unregister itself/register its successor; next movement calls successor once')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Pinned original APK or libairplay.so')
    parser.add_argument('unpacked_game', type=Path)
    parser.add_argument('--ndk', type=Path, default=os.environ.get('ANDROID_NDK_HOME'))
    args = parser.parse_args()
    if not args.ndk:
        parser.error('Provide --ndk or ANDROID_NDK_HOME')
    if zipfile.is_zipfile(args.source):
        with zipfile.ZipFile(args.source) as apk:
            legacy = apk.read('lib/armeabi/libairplay.so')
    else:
        legacy = args.source.read_bytes()
    assert hashlib.sha256(legacy).hexdigest() == ELF_SHA
    with tempfile.TemporaryDirectory(prefix='s3ce-pointer-proxy-') as temporary:
        for address in (0x21000000, 0xdb000000):
            probe = compile_probe(Path(args.ndk), Path(temporary)/'probe.elf', address)
            print(f'Compiled production C proxy text at {address:#x}')
            run(legacy, probe, args.unpacked_game)


if __name__ == '__main__':
    main()
