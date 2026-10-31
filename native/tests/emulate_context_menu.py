#!/usr/bin/env python3
"""Original context-menu render/hit/activation and compiled production ARM hook.

Requires pinned Unicorn plus the user-supplied unpacked S3E and Android NDK.
No original source program, assets, screenshots or reports are bundled.
Actual original constructors, COW arrays, Display/soft-float/trigonometry,
render geometry, bounds, gesture selection, timer and SceneGame action-ID
extraction execute. Graphics/font endpoints, allocation/free/memcpy, sound,
selection visuals and final world-action execution are explicitly modeled.
The portrait-dimension case checks Display's canonical max/min axes; Android
surface rotation and completion of a real interaction remain runtime gates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
from emulate_stack_bridge import load_elf, symbol_table

SOURCE_SHA = '8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a'
PREFERRED, OFFSET, EXTENT = 0x4a000000, 0xd2a0, 0x166ad8
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
SAVED = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
         UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11)
FP_SAVED = (UC_ARM_REG_D8, UC_ARM_REG_D9, UC_ARM_REG_D10, UC_ARM_REG_D11,
            UC_ARM_REG_D12, UC_ARM_REG_D13, UC_ARM_REG_D14, UC_ARM_REG_D15)
DIMENSIONS = ((480, 320, 1.0), (960, 640, 2.0), (1920, 1080, 3.375),
              (1080, 1920, 3.375), (2160, 1080, 3.375))
PROBE = r'''
#include <stddef.h>
#include <stdint.h>
uintptr_t __stack_chk_guard=0x13579bdfu;
__attribute__((noreturn)) void __stack_chk_fail(void){__builtin_trap();}
void *memcpy(void *dst,const void *src,size_t n){
 volatile unsigned char*d=dst;const volatile unsigned char*s=src;
 for(size_t i=0;i<n;i++)d[i]=s[i];return dst;
}
int memcmp(const void *a,const void *b,size_t n){
 const volatile unsigned char*x=a,*y=b;
 for(size_t i=0;i<n;i++)if(x[i]!=y[i])return x[i]-y[i];return 0;
}
'''


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def number(value):
    return struct.unpack('<f', struct.pack('<I', value))[0]


def compile_probe(ndk, directory, text):
    native = Path(__file__).resolve().parents[1]
    compiler = ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi26-clang'
    support, output = directory/'support.c', directory/f'context-{text:x}.elf'
    support.write_text(PROBE)
    # Match production C optimization, Thumb/PIC, visibility and stack protection.
    subprocess.run([str(compiler), '-std=gnu11', '-O2', '-mthumb', '-fPIC',
        '-Wall', '-Wextra', '-Werror', '-fvisibility=hidden', '-fstack-protector-strong',
        '-nostdlib', '-static',
        f'-Wl,-Ttext={text:#x},-e,s3ce_context_menu_bounds,--no-undefined',
        str(native/'context_menu.c'), str(support), '-o', str(output)], check=True)
    return output.read_bytes()


class Machine:
    def __init__(self, source, high):
        self.vm = v = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        v.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_A15)
        v.reg_write(UC_ARM_REG_C1_C0_2, v.reg_read(UC_ARM_REG_C1_C0_2) | 0x00f00000)
        v.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        self.code = 0xc0d9c000 if high else PREFERRED
        self.data = 0xe3000000 if high else self.code + EXTENT
        self.heap = 0xbc000000 if high else 0x60000000
        self.stack, self.next_heap = 0xf0000000, self.heap
        self.stack_top, self.stop = self.stack+0xf0000, self.stack+0xfff00
        self.code_length = 0x200000
        v.mem_map(self.code, self.code_length)
        v.mem_write(self.code, source[OFFSET:OFFSET+EXTENT])
        if high:
            v.mem_map(self.data, 0x20000)
        initialized, total = struct.unpack_from('<II', source, 0x18)
        assert (initialized, total) == (0x169010, 0x1806fc)
        v.mem_write(self.data, source[OFFSET+EXTENT:OFFSET+initialized])
        assert struct.unpack_from('<II', source, 0xddc) == (1, 0xbf88)
        count = struct.unpack_from('<I', source, 0xde4)[0]
        assert count == 12255
        for relative in struct.unpack_from('<'+'I'*count, source, 0xde8):
            address = self.relocate(relative)
            old = self.read(address)-PREFERRED
            assert 0 <= old < total
            self.write(address, self.relocate(old))
        v.mem_map(self.heap, 0x400000)
        v.mem_map(self.stack, 0x100000)
        self.boundaries, self.original_calls, self.sounds = {}, {}, []
        self.active_allocations = set()
        for offset in (0x132cac, 0x132ca4, 0x139368, 0x13c80c,
                       0x132c9c, 0x132c94, 0x135910, 0xcbc):
            self.hook(offset, self.memory_boundary)

    def relocate(self, relative):
        return self.code+relative if relative < EXTENT else self.data+relative-EXTENT

    def read(self, address):
        return struct.unpack('<I', self.vm.mem_read(address, 4))[0]

    def write(self, address, *values):
        self.vm.mem_write(address, struct.pack('<'+'I'*len(values),
                           *(value & 0xffffffff for value in values)))

    def allocate(self, length):
        result = self.next_heap
        self.next_heap += (max(length, 1)+15) & ~15
        assert self.next_heap <= self.heap+0x400000
        self.vm.mem_write(result, b'\xa5'*max(length, 1))
        self.active_allocations.add(result)
        return result

    def zero(self, length):
        result = self.allocate(length)
        self.vm.mem_write(result, bytes(length))
        return result

    def ret(self, value=None):
        if value is not None:
            self.vm.reg_write(UC_ARM_REG_R0, value & 0xffffffff)
        self.vm.reg_write(UC_ARM_REG_PC, self.vm.reg_read(UC_ARM_REG_LR))

    def hook(self, offset, callback):
        address = self.code+offset
        def wrapper(vm, pc, size, unused):
            callback(offset, [vm.reg_read(r) for r in REGS], vm.reg_read(UC_ARM_REG_SP))
        self.vm.hook_add(UC_HOOK_CODE, wrapper, begin=address, end=address)

    def memory_boundary(self, offset, args, sp):
        if offset in (0x132cac, 0x132ca4, 0x139368, 0x13c80c):
            self.ret(self.allocate(args[0]))
        elif offset in (0x132c9c, 0x132c94, 0x135910):
            if args[0]:
                assert args[0] in self.active_allocations
                self.active_allocations.remove(args[0])
            self.ret()
        else:
            self.vm.mem_write(args[0], bytes(self.vm.mem_read(args[1], args[2])))
            self.ret(args[0])

    def call(self, entry, args=(), absolute=False, limit=10000000):
        v = self.vm
        integers = {r: 0x98760000+i*0x101 for i, r in enumerate(SAVED)}
        floats = {r: 0x1122334455660000+i for i, r in enumerate(FP_SAVED)}
        for register, value in (*integers.items(), *floats.items()):
            v.reg_write(register, value)
        for i, register in enumerate(REGS):
            v.reg_write(register, args[i] & 0xffffffff if i < len(args) else 0)
        for i, value in enumerate(args[4:]):
            self.write(self.stack_top+i*4, value)
        guard = bytes.fromhex('b91273f0')*8
        v.mem_write(self.stack_top-0x8000, guard)
        v.mem_write(self.stack_top+0x80, guard)
        v.reg_write(UC_ARM_REG_SP, self.stack_top)
        v.reg_write(UC_ARM_REG_LR, self.stop)
        v.emu_start(entry if absolute else self.code+entry, self.stop, count=limit)
        assert v.reg_read(UC_ARM_REG_PC) == self.stop
        assert v.reg_read(UC_ARM_REG_SP) == self.stack_top
        assert all(v.reg_read(r) == value for r, value in integers.items())
        assert all(v.reg_read(r) == value for r, value in floats.items())
        assert bytes(v.mem_read(self.stack_top-0x8000, len(guard))) == guard
        assert bytes(v.mem_read(self.stack_top+0x80, len(guard))) == guard
        return v.reg_read(UC_ARM_REG_R0)

    def array(self, values):
        array = self.allocate(20)
        self.call(0x14343c, (array, len(values)))
        data = self.read(self.read(array+12)+8)
        self.write(data, *values)
        return array, data


def run_case(source, probe, high, width, height, scale):
    p = Machine(source, high)
    v, c = p.vm, p.code
    display, engine, scene, button, target = [p.zero(0x2000) for _ in range(5)]
    p.write(display, bits(scale))
    p.write(display+0x20, width, height, 0)
    p.write(p.read(c+0x866a4), display)
    p.write(p.read(c+0xedde0), engine)
    p.write(engine+0x40, scene)
    p.write(scene, c+0x15fac8)
    p.write(scene+0x20, engine)
    context = p.allocate(0x100)
    p.call(0x86584, (context,))
    metrics = p.read(c+0x866a8)
    action_ids = (0x10, 0x11, 0x12, 0x13)  # distinct synthetic IDs, no label claim
    options, option_data = p.array((4, 0xffffffff, 0, 0, 0, 101, 102, 103, 104))
    actions, _ = p.array((4, 0, 0, 0, 0, *action_ids))
    row_text, cancel, drawing, emitted, forwarded = [], [], [], [], []

    def endpoint(offset, args, sp):
        if offset in (0x92ec0, 0x922b4):
            drawing.append((offset, *args, bytes(v.mem_read(sp, 20))))
            p.ret()
        elif offset == 0x9203c:
            p.ret()
        elif offset == 0x92618:
            p.ret(bits(32))  # header cap only; independent of rows and bounds
        elif offset == 0xbb878:
            p.ret(button)
        elif offset == 0xe94c0:
            cancel.append(tuple(args[2:4]))
            p.ret()
        elif offset == 0x61750:
            row_text.append((args[2], *struct.unpack('<2i', v.mem_read(sp, 8))))
            p.ret()
        elif offset in (0x130b4c, 0x129d74):
            p.ret(0 if offset == 0x130b4c else 0xffffffff)
        elif offset == 0xfb490:
            payload = p.read(p.read(args[2]+12)+8)
            emitted.append((args[1], *(p.read(payload+i*4) for i in range(3))))
            # Continue through the actual SceneGame handler and selected-ID lookup.
        elif offset == 0x103280:
            forwarded.append((args[1], args[2], args[3], p.read(sp)))
            p.ret()
        else:
            p.ret()  # sound / selection-visual reset / focus owner bookkeeping

    for offset in (0x92ec0, 0x922b4, 0x9203c, 0x92618, 0xbb878, 0xe94c0,
                   0x61750, 0x130b4c, 0x129d74, 0xbf52c, 0xfb490, 0x103280,
                   0x101fec, 0x109c28, 0xbdba4):
        p.hook(offset, endpoint)

    def open_and_draw():
        row_text.clear(); cancel.clear(); drawing.clear()
        p.call(0x863dc, (context, options, actions, 0))
        p.call(0x857ac, (context, 0))
        assert tuple(t[0] for t in row_text) == (101, 102, 103, 104)
        return (tuple(row_text), tuple(cancel), tuple(drawing))

    before_draw = open_and_draw()
    original_bounds = struct.unpack('<4i', v.mem_read(context+0x30, 16))
    top = p.call(0xae458, (display, 0, 2))
    expected_bounds = (original_bounds[0], top, 200, 320)
    event, outer, data = [p.zero(0x100) for _ in range(3)]
    p.write(event+12, outer); p.write(outer+8, data)
    p.write(scene+0x628, p.read(context+0x84))
    p.write(scene+0x63c, p.read(context+0x98))
    p.write(scene+0x65c, context)

    def tap(x, y):
        p.write(data+4, x, y)
        p.write(option_data+8, 0xffffffff)
        p.write(context+0x74, 0)
        p.write(scene+0x40, 0)
        p.write(scene+0x1c0, 6)
        p.write(scene+0x298, target)
        v.mem_write(scene+0x616, b'\x01\x00')
        emitted.clear(); forwarded.clear()
        hit = p.call(0x11fb8c, (context, x, y))
        p.call(0x8560c, (context, 0, event))
        selected = p.read(option_data+8)
        selected = selected if selected < 0x80000000 else selected-0x100000000
        p.call(0x8560c, (context, 3, event))
        at_up = p.read(context+0x74)
        p.call(0x86368, (context, 400))
        at400 = p.read(context+0x74)
        p.call(0x86368, (context, 1))
        at401 = p.read(context+0x74)
        if 0 <= selected < 4:
            assert (at_up, at400, at401) == (1, 1, 0)
            assert emitted == [(11, 8, 0, 0xffffffff)]
            assert forwarded == [(action_ids[selected], target, 0, 0)]
        else:
            assert (at_up, at400, at401) == (0, 0, 0)
            assert not emitted and not forwarded
        return (hit, selected, tuple(emitted), tuple(forwarded))

    original = [tap(x, y) for _, x, y in before_draw[0]]
    source_before = bytes(v.mem_read(c, EXTENT))
    load_elf(v, probe, 0, set())
    symbols = symbol_table(probe)
    patch = symbols['s3ce_patch_context_menu'][0]
    helper = symbols['s3ce_context_menu_bounds'][0]
    assert patch & 1 and helper & 1
    patch_args = (c, p.code_length, c, EXTENT, helper)
    assert p.call(patch, patch_args, absolute=True) == 1
    assert p.call(patch, patch_args, absolute=True) == 2
    source_after = bytes(v.mem_read(c, EXTENT))
    assert source_before[:0x86310] == source_after[:0x86310]
    assert source_before[0x86338:] == source_after[0x86338:]
    words = struct.unpack('<10I', source_after[0x86310:0x86338])
    assert words == (0xe1a00004, 0xe59f100c, 0xe59fc00c, 0xe12fff3c,
                     0xea000004, 0xe1a00000, c, helper, 0xe1a00000, 0xe1a00000)
    after_draw = open_and_draw()
    assert before_draw == after_draw, 'Production hook changed visible draw inputs'
    assert struct.unpack('<4i', v.mem_read(context+0x30, 16)) == expected_bounds
    corrected = [tap(x, y) for _, x, y in after_draw[0]]
    # SceneGame deliberately keeps world taps raw but converts context-menu
    # input through its original virtual transform1009F8 -> Display AE4F0.
    xy = p.zero(8)
    p.write(scene+0x1c0, 6)
    v.mem_write(scene+0x616, b'\x00')
    p.write(xy, 30, 90)
    p.call(0x1009f8, (scene, xy, xy+4))
    assert (p.read(xy), p.read(xy+4)) == (30, 90)
    transformed_rows = []
    half_x, half_y = max(width, height)/2, min(width, height)/2
    for index, (_, x, y) in enumerate(after_draw[0]):
        raw_x = round(half_x+(x-half_x)*scale)
        raw_y = round(half_y+(y-half_y)*scale)
        p.write(xy, raw_x, raw_y)
        v.mem_write(scene+0x616, b'\x01')
        p.call(0x1009f8, (scene, xy, xy+4))
        actual = (p.read(xy), p.read(xy+4))
        assert abs(actual[0]-x) <= 1 and abs(actual[1]-y) <= 1
        result = tap(*actual)
        assert result[0:2] == (1, index)
        transformed_rows.append(dict(raw=[raw_x, raw_y], logical=actual,
                                     selected=result[1]))
    assert all(hit == 1 and selected == i for i, (hit, selected, *_)
               in enumerate(corrected))
    for item, result in zip(before_draw[0], original):
        _, x, y = item
        x0, y0, w, h = original_bounds
        assert result[0] == int(x0 <= x < x0+w and y0 <= y < y0+h)
    if scale == 1:
        assert original == corrected
    x0, y0, w, h = expected_bounds
    negative = ((x0-1, y0+h//2), (x0+w, y0+h//2),
                (x0+w//2, y0-1), (x0+w//2, y0+h), *after_draw[1])
    assert all(tap(x, y)[0:2] == (0, -1) for x, y in negative)
    # Preserve the existing nearest-row policy in the visual inter-row spaces.
    gaps = []
    for row in range(3):
        y = (after_draw[0][row][2]+after_draw[0][row+1][2]+1)//2
        selected = tap(x0+w//2, y)[1]
        assert selected == row+1
        gaps.append(selected)
    half_x, half_y = max(width, height)/2, min(width, height)/2
    raw_rows = [[half_x+(x-half_x)*scale, half_y+(y-half_y)*scale]
                for _, x, y in after_draw[0]]
    return dict(high=high, width=width, height=height, scale=scale,
                helper=hex(helper), originalBounds=original_bounds,
                correctedBounds=expected_bounds, rowLogical=after_draw[0],
                surfaceLandscapeRows=raw_rows, cancelLogical=after_draw[1],
                originalSelected=[x[1] for x in original],
                correctedSelected=[x[1] for x in corrected],
                actionIDs=list(action_ids), transformedRows=transformed_rows,
                worldInputTransformUnchanged=True, negativeChecks=len(negative),
                gapSelected=gaps, originalDrawingInputsUnchanged=True,
                actualProductionPatchAndHelper=True, abiAndStackChecks=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--ndk', type=Path,
                        default=Path(os.environ['ANDROID_NDK_HOME'])
                        if os.environ.get('ANDROID_NDK_HOME') else None)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.ndk is None:
        parser.error('--ndk or ANDROID_NDK_HOME is required')
    source = args.source.read_bytes()
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA, 'Unexpected source S3E'
    results = []
    with tempfile.TemporaryDirectory(prefix='s3ce-context-') as directory:
        for text in (0x21000000, 0xdb000000):
            probe = compile_probe(args.ndk, Path(directory), text)
            for high in (False, True):
                for width, height, scale in DIMENSIONS:
                    results.append(run_case(source, probe, high, width, height, scale))
    summary = dict(cases=len(results), rowChecks=len(results)*8,
                   negativeChecks=sum(r['negativeChecks'] for r in results),
                   gapChecks=len(results)*3, sourceInputTransformChecks=len(results)*5,
                   passAll=True, results=results)
    if args.output:
        args.output.write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k: value for k, value in summary.items() if k != 'results'}, indent=2))


if __name__ == '__main__':
    main()
