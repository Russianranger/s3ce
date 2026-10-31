#!/usr/bin/env python3
"""Trace the source APK's actual Thumb pointer input and polling routines.

The JNI dispatcher, ID tracking, position transformation and pointer update run
unaltered. Only device-init/orientation queries and callback delivery are mocked.
Requires Unicorn; accepts the pinned original APK or libairplay.so.
"""
import argparse
import hashlib
import struct
import zipfile
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                              UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR,
                              UC_ARM_REG_PC)
from emulate_gl_start import BASE, AUX, STACK, ELF_SHA, machine, word


class PointerTrace:
    def __init__(self, data):
        self.vm = machine(data)
        self.events = []
        self.pointer = BASE + 0x55d80
        self.surface = BASE + 0x5675c
        self.stop = AUX + 0xff0
        self.vm.mem_write(self.stop, b'\x70\x47')
        self.vm.mem_write(self.pointer, bytes(48))
        self.vm.mem_write(self.surface, bytes(0x80))
        word(self.vm, BASE + 0x53af0 + 0x10c, 1)  # initialized native mutex
        word(self.vm, self.surface + 0x2c, 1920)
        word(self.vm, self.surface + 0x30, 1080)
        self.vm.hook_add(UC_HOOK_CODE, self.hook)

    def hook(self, vm, address, size, _):
        if address == self.stop:
            vm.emu_stop()
            return
        if address == BASE + 0x2c3e8:  # s3eDeviceIsInitialised
            vm.reg_write(UC_ARM_REG_R0, 1)
        elif address == BASE + 0x2c428:  # s3eDeviceGetUserOrientation
            vm.reg_write(UC_ARM_REG_R0, 0)
        elif address in (BASE + 0x26c2c, BASE + 0x27064):
            device = vm.reg_read(UC_ARM_REG_R0)
            kind = vm.reg_read(UC_ARM_REG_R1)
            payload = vm.reg_read(UC_ARM_REG_R2)
            length = vm.reg_read(UC_ARM_REG_R3)
            values = struct.unpack('<' + 'i' * (length // 4),
                                   vm.mem_read(payload, length))
            self.events.append((device, kind, values))
            vm.reg_write(UC_ARM_REG_R0, 0)
        else:
            return
        vm.reg_write(UC_ARM_REG_PC, vm.reg_read(UC_ARM_REG_LR))

    def call(self, offset, args=()):
        vm = self.vm
        sp = STACK + 0x8000
        vm.reg_write(UC_ARM_REG_SP, sp)
        vm.reg_write(UC_ARM_REG_LR, self.stop | 1)
        for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1,
                                    UC_ARM_REG_R2, UC_ARM_REG_R3), args):
            vm.reg_write(register, value & 0xffffffff)
        for i, value in enumerate(args[4:]):
            word(vm, sp + i * 4, value & 0xffffffff)
        vm.emu_start(BASE + offset + 1, 0, count=10000)
        assert vm.reg_read(UC_ARM_REG_PC) == self.stop
        return vm.reg_read(UC_ARM_REG_R0)

    def motion(self, pointer_id, event, x, y):
        before = len(self.events)
        self.call(0x2148c, (0, 0, pointer_id, event, x, y))
        return self.events[before:]

    def state(self):
        self.call(0x37548)  # source s3ePointerUpdate
        x = self.call(0x375e0)
        y = self.call(0x3759c)
        button = self.call(0x37624, (0,))
        return x, y, button


def test_source(data):
    for pointer_id in (0, 7, 31):
        trace = PointerTrace(data)
        native_id = pointer_id + 1
        assert trace.motion(pointer_id, 4, 1500, 600) == [
            (6, 2, (native_id, 1, 1500, 600)), (6, 0, (0, 1, 1500, 600))]
        assert word(trace.vm, trace.pointer + 0x24) == native_id
        assert trace.state() == (1500, 600, 3)  # held | pressed
        for x, y in ((1450, 590), (1300, 580), (1100, 550), (800, 510)):
            assert trace.motion(pointer_id, 6, x, y) == [
                (6, 3, (native_id, x, y)), (6, 1, (x, y))]
            assert trace.state() == (x, y, 1)  # held, no new press
        assert trace.motion(pointer_id, 5, 800, 510) == [
            (6, 2, (native_id, 0, 800, 510)), (6, 0, (0, 0, 800, 510))]
        assert trace.state() == (800, 510, 4)  # released
        assert word(trace.vm, trace.pointer + 0x24) == 0
        assert trace.state() == (800, 510, 0)
        print(f'PASS source Thumb swipe ID={pointer_id}: down/move/up callbacks '
              'and polled position/button state match each event')

    trace = PointerTrace(data)
    trace.motion(7, 4, 100, 200)
    trace.motion(31, 4, 900, 700)
    assert trace.motion(31, 6, 850, 650) == [(6, 3, (32, 850, 650))]
    assert trace.state() == (100, 200, 3)
    assert trace.motion(7, 6, 200, 300) == [
        (6, 3, (8, 200, 300)), (6, 1, (200, 300))]
    assert trace.state() == (200, 300, 1)
    trace.motion(31, 5, 850, 650)
    assert trace.state() == (200, 300, 1)
    trace.motion(7, 5, 200, 300)
    assert trace.state() == (200, 300, 4)
    print('PASS source Thumb second pointer cannot steal primary drag or release it')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', help='Pinned original APK or libairplay.so')
    args = parser.parse_args()
    if zipfile.is_zipfile(args.source):
        with zipfile.ZipFile(args.source) as apk:
            data = apk.read('lib/armeabi/libairplay.so')
    else:
        with open(args.source, 'rb') as source:
            data = source.read()
    assert hashlib.sha256(data).hexdigest() == ELF_SHA
    test_source(data)
