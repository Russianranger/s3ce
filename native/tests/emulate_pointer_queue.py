#!/usr/bin/env python3
"""Execute original pointer registration, owned queue, dispatch and ARM callback.

Includes real IwMemcpy and the original StackSwitch=1 API/callback gateways.
Only allocation/free, locks, device readiness/orientation, timers/platform wait,
and config IO are mocks.
No PointerUpdate is called: this also proves that published polling state can
remain zero while a callback-only game receives every coordinate correctly.
Requires the optional pinned Unicorn dependency and the user-supplied source.
"""
import argparse
import hashlib
import struct
import zipfile
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
    UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
    UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR,
)
from emulate_gl_start import BASE, AUX, STACK, ELF_SHA, machine, word

SAVED_REGISTERS = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
                   UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
                   UC_ARM_REG_R10, UC_ARM_REG_R11)


class QueueProof:
    def __init__(self, data, switching, cpu_model=None):
        self.vm = machine(data, cpu_model)
        self.switching = switching
        self.os_sp, self.game_sp = STACK + 0xe000, STACK + 0x7000
        self.stop = AUX + 0xff0
        self.vm.mem_write(self.stop, b'\x70\x47')
        self.callbacks = {AUX + 0x1000: 0, AUX + 0x1100: 1}
        for address in self.callbacks:
            self.vm.mem_write(address, b'\x1e\xff\x2f\xe1')  # ARM BX LR
        self.next_allocation = AUX + 0x4000
        self.received = []
        self.visits = {}
        self.cookie = 0x76543210
        # Native mutex handle, surface dimensions and callbacks-ready gate.
        word(self.vm, BASE + 0x53af0 + 0x10c, 1)
        word(self.vm, BASE + 0x5675c + 0x2c, 1920)
        word(self.vm, BASE + 0x5675c + 0x30, 1080)
        self.vm.mem_write(BASE + 0x54580 + 0x55, b'\x01')
        self.vm.hook_add(UC_HOOK_CODE, self.hook)
        # Execute the source config reader/setter, rather than inventing their
        # private StackSwitch or saved-loader-stack state.
        self.call(BASE + 0x3c945)
        self.call(BASE + 0x3c83d, (self.os_sp,))
        assert self.vm.mem_read(BASE + 0x54b68 + 0x18, 1)[0] == switching
        # Original s3eGetSymbolsInfo slots: PointerRegister is Int32/generic;
        # DeviceYield is Int64/generic. Both use the same full stack gateway.
        assert self.vm.mem_read(BASE + 0x43f28 + 425, 1)[0] == 4
        assert self.vm.mem_read(BASE + 0x43f28 + 338, 1)[0] == 8

    def hook(self, cpu, address, size, unused):
        offset = address - BASE
        if address == self.stop:
            cpu.emu_stop()
            return
        if offset in (0x3752c, 0x26da0, 0x26c2c, 0x20bbc,
                      0x2736c, 0x27064, 0x3c558):
            self.visits[offset] = self.visits.get(offset, 0) + 1
        if address in self.callbacks:
            kind = self.callbacks[address]
            payload = cpu.reg_read(UC_ARM_REG_R0)
            length = 16 if kind == 0 else 8
            values = struct.unpack('<' + 'i' * (length // 4),
                                   cpu.mem_read(payload, length))
            assert cpu.reg_read(UC_ARM_REG_R1) == self.cookie
            if self.switching:
                sp = cpu.reg_read(UC_ARM_REG_SP)
                assert self.game_sp - 0x1000 < sp < self.game_sp
                assert word(cpu, BASE + 0x54b68 + 8) != 0
            self.received.append((kind, values))
            cpu.reg_write(UC_ARM_REG_R0, 0x6000 + kind)
            return  # Execute the callback's actual BX LR.
        if offset == 0x2c3e8:  # DeviceIsInitialised
            cpu.reg_write(UC_ARM_REG_R0, 1)
        elif offset == 0x2c428:  # DeviceGetUserOrientation
            cpu.reg_write(UC_ARM_REG_R0, 0)
        elif offset == 0x35ff0:  # External loader allocation boundary.
            length = cpu.reg_read(UC_ARM_REG_R0)
            address = self.next_allocation
            self.next_allocation = (address + length + 7) & ~7
            assert self.next_allocation < AUX + 0xf000
            cpu.mem_write(address, bytes(length))
            cpu.reg_write(UC_ARM_REG_R0, address)
        elif offset in (0x35fa0, 0x35f8c, 0x2c7a4, 0x36250,
                        0x3d4c4, 0x223a0, 0x22344):
            cpu.reg_write(UC_ARM_REG_R0, 0)  # Locks/notify/free, single-thread model.
        elif offset == 0x3d654:
            cpu.reg_write(UC_ARM_REG_R0, 100)
            cpu.reg_write(UC_ARM_REG_R1, 0)
        elif offset == 0x2972c:
            cpu.reg_write(UC_ARM_REG_R0, self.switching)
        elif offset in (0x1b148, 0x2b9ec):
            raise AssertionError(f'Unexpected original stack/error path {offset:#x}')
        else:
            return
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    def call(self, entry, arguments=(), sp=None):
        cpu = self.vm
        sp = self.os_sp if sp is None else sp
        sentinels = {register: 0x44000000 + i * 0x10101
                     for i, register in enumerate(SAVED_REGISTERS)}
        for register, value in sentinels.items():
            cpu.reg_write(register, value)
        cpu.reg_write(UC_ARM_REG_SP, sp)
        cpu.reg_write(UC_ARM_REG_LR, self.stop | 1)
        for i, register in enumerate((UC_ARM_REG_R0, UC_ARM_REG_R1,
                                      UC_ARM_REG_R2, UC_ARM_REG_R3)):
            cpu.reg_write(register, arguments[i] if i < len(arguments) else 0)
        for i, value in enumerate(arguments[4:]):
            word(cpu, sp + i * 4, value)
        cpu.emu_start(entry, 0, count=100000)
        assert cpu.reg_read(UC_ARM_REG_PC) == self.stop
        assert cpu.reg_read(UC_ARM_REG_SP) == sp
        for register, value in sentinels.items():
            assert cpu.reg_read(register) == value, (register, entry)
        return cpu.reg_read(UC_ARM_REG_R0)

    def api(self, target, arguments=(), return_size=4):
        if not self.switching:
            return self.call(BASE + target + 1, arguments, self.game_sp)
        # Same real ARM import-veneer template used by the source loader.
        veneer = AUX + 0x300
        gateway = {0: 0x3c7f0, 4: 0x3c808, 8: 0x3c81c}[return_size]
        self.vm.mem_write(veneer, struct.pack('<IIII', 0xe59fc000, 0xe59ff000,
                                             BASE + target + 1, BASE + gateway))
        before = self.fibre_state()
        result = self.call(veneer, arguments, self.game_sp)
        assert self.fibre_state() == before
        return result

    def fibre_state(self):
        return (word(self.vm, BASE + 0x54b68 + 8),
                self.vm.mem_read(BASE + 0x54b68 + 0xc, 1)[0],
                word(self.vm, BASE + 0x56758))

    def register(self, kind):
        callback = next(address for address, event in self.callbacks.items()
                        if event == kind)
        assert self.api(0x3752c, (kind, callback, self.cookie)) == 0

    def motion(self, pointer_id, kind, x, y):
        self.call(BASE + 0x2148d, (0, 0, pointer_id, kind, x, y))
        # The callback-only game has not called the separate polling API.
        assert bytes(self.vm.mem_read(BASE + 0x55d80, 5)) == bytes(5)
        assert bytes(self.vm.mem_read(BASE + 0x55d80 + 0xc, 8)) == bytes(8)

    def dispatch(self):
        self.api(0x2c660, (0,), return_size=8)  # Actual game-facing DeviceYield.
        assert word(self.vm, BASE + 0x53d30) == 0


def test(data):
    expected = [(0, (0, 1, 1500, 600)), (1, (1400, 590)),
                (1, (1200, 500)), (0, (0, 0, 1100, 450))]
    for switching in (0, 1):
        for pointer_id in (0, 7, 31):
            proof = QueueProof(data, switching)
            proof.register(0)
            proof.register(1)
            for kind, x, y in ((4, 1500, 600), (6, 1400, 590),
                               (6, 1200, 500), (5, 1100, 450)):
                proof.motion(pointer_id, kind, x, y)
                assert not proof.received  # Owned FIFO, not immediate delivery.
            assert word(proof.vm, BASE + 0x53d30) != 0
            proof.dispatch()
            assert proof.received == expected
            assert proof.visits[0x20bbc] == 4  # Real 8/16-byte copies executed.
            assert proof.visits[0x3c558] == 4  # Real callback gateway executed.
            proof.dispatch()  # Already drained: no duplicate callbacks.
            assert proof.received == expected
            print(f'PASS original queue StackSwitch={switching} pointerID={pointer_id}: '
                  'FIFO 8/16-byte payloads/cookie, actual callback stack, r4-r11/SP '
                  'restoration; published polling state remains zero')
    # A missing movement registration is legitimately filtered at enqueue time.
    proof = QueueProof(data, 1)
    proof.register(0)
    proof.motion(0, 4, 1500, 600)
    proof.motion(0, 6, 1400, 590)
    proof.motion(0, 5, 1100, 450)
    proof.dispatch()
    assert proof.received == [expected[0], expected[-1]]
    print('PASS original queue filters movement when no event1 callback is registered')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Pinned original APK or libairplay.so')
    args = parser.parse_args()
    if zipfile.is_zipfile(args.source):
        with zipfile.ZipFile(args.source) as apk:
            source = apk.read('lib/armeabi/libairplay.so')
    else:
        source = args.source.read_bytes()
    assert hashlib.sha256(source).hexdigest() == ELF_SHA
    test(source)
