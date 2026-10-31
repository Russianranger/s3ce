"""Actual source-game pointer callbacks, AppEngine queues, and SceneMenu FSM.

Reusable by the legacy queue/proxy ARM execution tests. Only debug imports and
the UI side effects after the gesture state's real write are mocked. Actual
callback bodies, both coordinate transforms, queue adapters, frame drain, menu
event handler, base forwarding, gesture decisions, and square root execute.
The SceneMenu state1 fast exit bypasses unrelated menu-specific effects AFTER
the real shared gesture FSM. This does not emulate the final CAS rotation UI.
"""
import argparse
import hashlib
import struct
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *

PREFERRED = 0x4a000000
CODE_OFFSET = 0xd2a0
CODE_EXTENT = 0x166ad8
SOURCE_SHA = '8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a'
SAVED = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
         UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11)


class GamePointerFixture:
    def __init__(self, vm, source, code_base=0xc0cb8000, heap_base=0xbfc00000,
                 data_base=0xd1000000):
        source = Path(source).read_bytes() if isinstance(source, (str, Path)) else source
        assert hashlib.sha256(source).hexdigest() == SOURCE_SHA
        self.vm, self.code_base, self.heap_base, self.data_base = vm, code_base, heap_base, data_base
        self.next_heap = heap_base
        vm.mem_map(code_base, 0x200000)
        vm.mem_write(code_base, source[CODE_OFFSET:CODE_OFFSET + CODE_EXTENT])
        # IwS3ERead allocates initialized data/BSS independently from the code
        # arena. The code tail is a veneer arena, not the preferred-VMA globals.
        vm.mem_map(data_base, 0x20000)
        vm.mem_write(data_base, source[CODE_OFFSET + CODE_EXTENT:CODE_OFFSET + 0x169010])
        vm.mem_map(heap_base, 0x100000)
        self.received, self.transitions = [], []
        self.transition_contexts = []

        # Relocate only the explicit literal pools / vtable entries reached by
        # this test; do not accidentally rewrite conditional ARM branch words.
        for offset in (0x3af78, 0x3af7c, 0x3afdc, 0x3afe0, 0x11644c, 0xedde0):
            value = self.read(code_base + offset)
            assert PREFERRED <= value < PREFERRED + 0x200000
            assert value >= PREFERRED + CODE_EXTENT
            self.write(code_base + offset, data_base + value - PREFERRED - CODE_EXTENT)
        for offset, count in ((0x15f690, 26), (0x15fb70, 12), (0xbdc98, 7)):
            for i in range(count):
                value = self.read(code_base + offset + 4 * i)
                assert PREFERRED <= value < PREFERRED + 0x200000
                self.write(code_base + offset + 4 * i, code_base + value - PREFERRED)

        self.app_engine = self.allocate()
        self.scene = self.allocate(0x2000)
        self.display = self.allocate()
        self.write(self.app_engine, code_base + 0x15f690)
        self.write(self.app_engine + 0x40, self.scene)
        self.write(self.app_engine + 0x330, 0)
        self.write(self.scene, code_base + 0x15fb70)
        self.write(self.scene + 0x1ac, 1)  # exit AFTER shared gesture handling
        self.write(self.display, 0x3f800000)  # actual float scale1.0
        self.write(self.display + 0x20, 1920, 1080, 0)  # landscape, identity orientation
        self.write(data_base + 0x54, self.display)
        self.write(data_base + 0xa0, self.app_engine)
        self.write(data_base + 0xfc, self.app_engine)

        outer, self.counts_data = self.allocate(), self.allocate()
        self.write(outer + 8, self.counts_data)
        self.write(self.app_engine + 0x340, outer)
        self.queues = {}
        for offset in (0x354, 0x368, 0x37c, 0x390, 0x3a4):
            outer, elements = self.allocate(), self.allocate()
            self.write(outer + 8, elements)
            self.write(self.app_engine + offset, outer)
            self.queues[offset] = []
            for buffer in range(2):
                inner, data = self.allocate(), self.allocate()
                self.write(inner + 8, data)
                self.write(elements + buffer * 20 + 12, inner)
                self.queues[offset].append(data)
        record, self.event_data = self.allocate(), self.allocate()
        self.write(record + 8, self.event_data)
        self.write(self.app_engine + 0x3b8, record)
        self.button_address, self.move_address = code_base + 0x3aeb4, code_base + 0x3af84
        vm.hook_add(UC_HOOK_CODE, self.hook)

    def read(self, address):
        return struct.unpack('<I', self.vm.mem_read(address, 4))[0]

    def write(self, address, *values):
        self.vm.mem_write(address, struct.pack('<' + 'I' * len(values),
                                             *(value & 0xffffffff for value in values)))

    def allocate(self, length=0x1000):
        address = self.next_heap
        self.next_heap += (length + 0xfff) & ~0xfff
        assert self.next_heap <= self.heap_base + 0x100000
        return address

    def hook(self, vm, address, size, unused):
        offset = address - self.code_base
        if address in (self.button_address, self.move_address):
            count = 4 if address == self.button_address else 2
            payload = struct.unpack('<' + 'i' * count, vm.mem_read(vm.reg_read(UC_ARM_REG_R0), count * 4))
            self.received.append((0 if count == 4 else 1, payload,
                                  vm.reg_read(UC_ARM_REG_R1), vm.reg_read(UC_ARM_REG_R9),
                                  vm.reg_read(UC_ARM_REG_SP)))
        elif offset in (0xa2c, 0x3c4):
            # Button-only temporary debug string construction/output; neither
            # value is used by the later input path.
            vm.reg_write(UC_ARM_REG_PC, vm.reg_read(UC_ARM_REG_LR))
        elif offset == 0xbe2fc:
            self.transition_contexts.append((vm.reg_read(UC_ARM_REG_SP), vm.reg_read(UC_ARM_REG_LR),
                                             {r: vm.reg_read(r) for r in SAVED}))
        elif offset == 0xbe324:
            # Let the original helper set old/new state; then skip allocations,
            # timers and generated UI events outside this fixture's scope.
            scene = vm.reg_read(UC_ARM_REG_R4)
            self.transitions.append((self.read(scene + 0x88), self.read(scene + 0x84)))
            sp, lr, registers = self.transition_contexts.pop()
            for register, value in registers.items():
                vm.reg_write(register, value)
            vm.reg_write(UC_ARM_REG_SP, sp)
            vm.reg_write(UC_ARM_REG_PC, lr)
        elif offset == 0xb7b04:
            raise AssertionError('Unexpected real AppEngine pointer queue overflow')

    def queued(self, buffer):
        return [tuple(self.read(self.queues[offset][buffer] + 4 * i)
                      for offset in (0x354, 0x368, 0x37c, 0x390, 0x3a4))
                for i in range(self.read(self.counts_data + buffer * 4))]

    def snapshot(self):
        return {'active_buffer': self.read(self.app_engine + 0x330),
                'counts': (self.read(self.counts_data), self.read(self.counts_data + 4)),
                'state': self.read(self.scene + 0x84), 'primary': self.read(self.scene + 0x90),
                'origin': (self.read(self.scene + 0x98), self.read(self.scene + 0x9c)),
                'current': (self.read(self.scene + 0xa0), self.read(self.scene + 0xa4))}

    def drain(self, stack_top, return_pc):
        self.vm.reg_write(UC_ARM_REG_R0, self.app_engine)
        self.vm.reg_write(UC_ARM_REG_SP, stack_top)
        self.vm.reg_write(UC_ARM_REG_LR, return_pc)
        self.vm.emu_start(self.code_base + 0xece3c, return_pc & ~1, count=100000)
        assert self.vm.reg_read(UC_ARM_REG_PC) == (return_pc & ~1)


def standalone(source, code_base, heap_base, stack_base):
    vm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    data_base = 0x68000000 if code_base < 0x80000000 else 0xd1000000
    fixture = GamePointerFixture(vm, source, code_base, heap_base, data_base)
    vm.mem_map(stack_base, 0x10000)
    stop = stack_base + 0xff00
    payload = fixture.allocate()
    r9_cookie = 0xe2345678
    expected = []
    def event(kind, x, y):
        fixture.write(payload, *((0, 1 if kind == 0 else 0, x, y) if kind != 1 else (x, y)))
        vm.reg_write(UC_ARM_REG_R0, payload)
        vm.reg_write(UC_ARM_REG_R1, 0xf1234567)
        vm.reg_write(UC_ARM_REG_R9, r9_cookie)
        vm.reg_write(UC_ARM_REG_SP, stack_base + 0xf000)
        vm.reg_write(UC_ARM_REG_LR, stop)
        vm.emu_start(fixture.move_address if kind == 1 else fixture.button_address, stop, count=100000)
        assert vm.reg_read(UC_ARM_REG_PC) == stop
        assert vm.reg_read(UC_ARM_REG_R9) == r9_cookie
        expected.append((kind, x, y, 0, 1 if kind == 0 else 0))
        assert fixture.queued(fixture.read(fixture.app_engine + 0x330)) == [expected[-1]]
        fixture.drain(stack_base + 0xf000, stop)
        assert fixture.snapshot()['counts'] == (0, 0)
        assert vm.reg_read(UC_ARM_REG_R9) == r9_cookie
    event(0, 500, 600)
    assert fixture.snapshot()['state'] == 1
    event(1, 505, 600)
    assert fixture.snapshot()['state'] == 1
    event(1, 520, 600)
    assert fixture.snapshot()['state'] == 3
    event(1, 900, 630)
    assert fixture.snapshot()['current'] == (900, 630)
    event(2, 900, 630)
    assert fixture.snapshot()['state'] == 0
    assert fixture.transitions == [(0, 1), (1, 3), (3, 0)]
    assert len(fixture.received) == 5
    assert all(row[2] == 0xf1234567 and row[3] == r9_cookie
               and stack_base <= row[4] < stack_base + 0x10000 for row in fixture.received)
    print(f'PASS actual game callback->orientation->queue->drain->menu transform->FSM '
          f'code={code_base:#x} data={data_base:#x} heap={heap_base:#x} stack={stack_base:#x}; '
          'DOWN/5px/20px/400px/UP states1/1/3/3/0, R9 and cookie preserved')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('unpacked_game')
    args = parser.parse_args()
    standalone(args.unpacked_game, 0x4a000000, 0x60000000, 0x70000000)
    standalone(args.unpacked_game, 0xc0cb8000, 0xbfc00000, 0xbff00000)
