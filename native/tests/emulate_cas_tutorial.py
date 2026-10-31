#!/usr/bin/env python3
"""Execute the original CAS hint layout, button tap and phase12->13 route.

Requires the optional pinned Unicorn dependency and the user-supplied unpacked
S3E image. Sprite rendering/audio, generic temporary-array allocation/free and
post-commit phase resource creation are modeled. Actual layout arithmetic,
circle hit testing, pointer routing, 400ms button animation, generated action4,
SceneMenu switch/mask/gates and phase writes execute as original ARM code.
"""
import argparse
import struct
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
from game_pointer_fixture import GamePointerFixture, PREFERRED, SAVED


class TutorialProof:
    def __init__(self, source, high=False, body_height=45):
        self.vm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        base, heap, data, stack = ((0xc0fae000, 0xbf000000, 0xe3000000, 0xbff00000)
            if high else (PREFERRED, 0x60000000, 0x68000000, 0x70000000))
        self.game = GamePointerFixture(self.vm, source, base, heap, data)
        self.base, self.scene, self.engine = base, self.game.scene, self.game.app_engine
        self.vm.mem_map(stack, 0x10000)
        self.sp, self.stop = stack + 0xf000, stack + 0xff00
        self.hint, self.button, buttons, items, children = (self.game.allocate() for _ in range(5))
        self.event, wrapper, self.payload, self.point = (self.game.allocate() for _ in range(4))
        self.phase_frames, self.actions = [], []
        self.layout_stop = self.bbox_stop = False
        self.body_height = body_height
        # Only source-defined code pointers reached by this proof are relocated.
        for offset, count in ((0x114578, 39), (0xe9c84, 7)):
            for i in range(count):
                value = self.game.read(base + offset + i * 4)
                assert PREFERRED <= value < PREFERRED + 0x166ad8
                self.game.write(base + offset + i * 4, base + value - PREFERRED)
        button_vtable = self.game.read(base + 0xe9a74) - PREFERRED
        for i in range(10):
            value = self.game.read(base + button_vtable + i * 4)
            assert PREFERRED <= value < PREFERRED + 0x166ad8
            self.game.write(base + button_vtable + i * 4, base + value - PREFERRED)
        g = self.game
        g.write(self.engine + 8, 1920, 1080, 0)
        g.write(self.scene + 0x20, self.engine)
        g.write(self.scene + 0x1ac, 12)
        g.write(self.scene + 0xf8, 0xffffffff)
        g.write(self.scene + 0x1bc, 0)
        self.vm.mem_write(self.engine + 0x420, b'\x00')
        self.vm.mem_write(self.engine + 0x430, b'\x01')
        g.write(self.scene + 0x54, 1, children)
        g.write(children, self.button)
        g.write(self.scene + 0x68, buttons)
        g.write(buttons + 8, items)
        g.write(items + 8, self.button)  # action4 -> bit index2
        # Original action4 constructor fields (E96A8/E99E4).
        g.write(self.button, base + button_vtable)
        g.write(self.button + 0x28, 1)
        g.write(self.button + 0x2c, 0, 0xffffffff)
        g.write(self.button + 0x3c, 35)
        g.write(self.button + 0x50, 4)
        g.write(self.button + 0x58, 119, 122, 122)
        g.write(self.button + 0x80, 20)
        g.write(self.hint + 0x74, 1, 1)  # opened, type1 message box
        g.write(self.hint + 0x98, 4)
        g.write(self.hint + 0xa4, 296)
        g.write(self.hint + 0xb0, body_height)
        g.write(self.event + 0xc, wrapper)
        g.write(wrapper + 8, self.payload)
        g.write(self.game.display, struct.unpack('<I', struct.pack('<f', 3.375))[0])
        self.vm.hook_add(UC_HOOK_CODE, self.hook)

    def hook(self, vm, address, size, unused):
        offset = address - self.base
        if self.layout_stop and offset == 0xe94f4:
            vm.emu_stop()  # Original button draw already stored hit center.
        elif self.bbox_stop and offset == 0x92a28:
            vm.emu_stop()  # Original scale/bias/min/max writes have completed.
        elif offset in (0x92bb0, 0x922b4, 0xbf52c):
            vm.reg_write(UC_ARM_REG_PC, vm.reg_read(UC_ARM_REG_LR))  # sprite/audio only
        elif offset == 0x14343c:
            # Generic temporary event-array allocation; payload words remain
            # written by the original gesture/action emitter afterward.
            destination = vm.reg_read(UC_ARM_REG_R0)
            record, array = self.game.allocate(), self.game.allocate()
            self.game.write(destination, 0, 0, vm.reg_read(UC_ARM_REG_R1), record)
            self.game.write(record + 8, array)
            vm.reg_write(UC_ARM_REG_PC, vm.reg_read(UC_ARM_REG_LR))
        elif offset == 0x1435e0:
            vm.reg_write(UC_ARM_REG_PC, vm.reg_read(UC_ARM_REG_LR))  # release temp array
        elif offset == 0x114498 and vm.reg_read(UC_ARM_REG_R1) == 11:
            event = vm.reg_read(UC_ARM_REG_R2)
            record = self.game.read(event + 0xc)
            self.actions.append(self.game.read(self.game.read(record + 8)))
        elif offset == 0x116944:
            self.phase_frames.append((vm.reg_read(UC_ARM_REG_SP), vm.reg_read(UC_ARM_REG_LR),
                {register: vm.reg_read(register) for register in SAVED}))
        elif offset == 0x116970:
            # The real prefix has written previous/current phase and reset its
            # substate. Skip new CAS model/resource creation after that commit.
            sp, lr, saved = self.phase_frames.pop()
            for register, value in saved.items(): vm.reg_write(register, value)
            vm.reg_write(UC_ARM_REG_SP, sp)
            vm.reg_write(UC_ARM_REG_PC, lr)

    def call(self, offset, *arguments):
        for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), arguments):
            self.vm.reg_write(register, value)
        self.vm.reg_write(UC_ARM_REG_SP, self.sp)
        self.vm.reg_write(UC_ARM_REG_LR, self.stop)
        self.vm.emu_start(self.base + offset, self.stop, count=200000)
        if not self.layout_stop and not self.bbox_stop:
            assert self.vm.reg_read(UC_ARM_REG_PC) == self.stop
            assert self.vm.reg_read(UC_ARM_REG_SP) == self.sp

    def metric_width(self):
        # Decoded M3G sprite96 input: raw vertices +/-296,+/-32 and VBscale0.5.
        # Stream deserialization is outside this proof. The actual scale getter,
        # bounding-box arithmetic and Graphics::getWidth execute unchanged.
        g = self.game
        vertex_buffer, vertex_array, properties, properties_record, properties_data = (
            g.allocate() for _ in range(5))
        vector, vector_record, vector_data, positions_record, positions_data = (
            g.allocate() for _ in range(5))
        g.write(vertex_buffer + 0x30, vertex_array, 0x3f000000, 0, 0, 0)
        g.write(properties + 0xc, properties_record)
        g.write(properties_record + 8, properties_data)
        self.call(0x1234d4, vertex_buffer, properties)
        assert self.vm.reg_read(UC_ARM_REG_R0) == vertex_array
        assert g.read(properties_data) == 0x3f000000
        g.write(vector + 0xc, vector_record)
        g.write(vector_record + 8, vector_data)
        g.write(positions_record + 8, positions_data)
        self.vm.mem_write(positions_data, struct.pack('<12f',
            -296,32,0, -296,-32,0, 296,32,0, 296,-32,0))
        g.write(self.sp + 0x30, properties_record)
        g.write(self.sp + 0x18, positions_record)
        g.write(self.sp + 0x38, 4)
        g.write(self.sp + 0x20, 3)
        self.vm.reg_write(UC_ARM_REG_R10, vector)
        for register in (UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R9, UC_ARM_REG_R11):
            self.vm.reg_write(register, 0)
        self.bbox_stop = True
        self.call(0x92838)
        self.bbox_stop = False
        assert struct.unpack('<4f', self.vm.mem_read(vector_data, 16)) == (-148,-16,148,16)
        graphics, array, entries = (g.allocate() for _ in range(3))
        g.write(graphics + 0x88, array)
        g.write(array + 8, entries)
        g.write(entries + 96 * 20 + 0xc, vector_record)
        self.call(0x925c4, graphics, 96)
        assert struct.unpack('<f', struct.pack('<I', self.vm.reg_read(UC_ARM_REG_R0)))[0] == 296

    def layout(self):
        self.layout_stop = True
        self.call(0x7fdfc, self.hint, self.engine + 0x114)
        self.layout_stop = False
        center = (self.game.read(self.button + 0x34), self.game.read(self.button + 0x38))
        assert center == (823, int(540 - (self.body_height + 100) / 2 + 23))
        self.game.write(self.point, *center)
        self.call(0xae5a0, self.game.display, self.point, self.point + 4)
        return center, (self.game.read(self.point), self.game.read(self.point + 4))

    def pointer(self, kind, raw_x, raw_y):
        self.game.write(self.point, raw_x, raw_y)
        self.call(0xae4f0, self.game.display, self.point, self.point + 4)
        self.game.write(self.payload, 0, self.game.read(self.point), self.game.read(self.point + 4))
        self.call(0x114498, self.scene, kind, self.event)


def run(source, high, body_height):
    proof = TutorialProof(source, high, body_height)
    proof.metric_width()
    logical, physical = proof.layout()
    for x, y in ((1418, 742), (1244, 707)):
        proof.pointer(0, x, y)
        proof.pointer(2, x, y)
        proof.call(0xe9658, proof.button, 401)
        assert proof.game.read(proof.scene + 0x1ac) == 12 and not proof.actions
    proof.pointer(0, 500, 370)
    assert proof.game.read(proof.button + 0x2c) == 1
    proof.pointer(2, 500, 370)
    assert proof.game.read(proof.button + 0x2c) == 3
    assert proof.game.read(proof.scene + 0x1ac) == 12
    proof.call(0xe9658, proof.button, 400)
    assert proof.game.read(proof.scene + 0x1ac) == 12 and not proof.actions
    proof.call(0xe9658, proof.button, 1)
    assert proof.actions == [4]
    assert proof.game.read(proof.scene + 0x1ac) == 13
    print(f'PASS original CAS tutorial high={high}: actual scale/bbox/getWidth296, bodyHeight={body_height} '
        f'layout logical={logical} physical={physical}; report taps miss; '
        'raw500,370 DOWN/UP +401ms -> actual circle/button/action4 -> phase13')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('unpacked_game', type=Path)
    args = parser.parse_args()
    for high in (False, True):
        for body_height in (45, 60, 90): run(args.unpacked_game, high, body_height)
