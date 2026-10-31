#!/usr/bin/env python3
"""Execute source DLC/image shutdown and the compiled production order repair.

Uses the user-supplied pinned S3E and NDK; bundles no game data. Original manager
construction, pack/image constructor prefixes, retain/store, all owning
cleanup bodies, Display destruction and CacheGLES destruction execute. The
fixture represents one parsed DLC pack with an uploaded image. Filesystem lookup,
GPU deletion and unrelated subsystem termination are explicit boundaries.
Low and high split mappings use every original S3E relocation. The complete
original main cleanup sequence executes with its real stack frame/epilogue.
This is source/ABI validation, not an Android device shutdown acceptance test.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
from emulate_context_menu import Machine, PROBE, REGS, SAVED, FP_SAVED, SOURCE_SHA, EXTENT
from emulate_stack_bridge import load_elf, symbol_table


def compile_probe(ndk, directory, text):
    native = Path(__file__).resolve().parents[1]
    compiler = ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi26-clang'
    support, output = directory/'support.c', directory/f'shutdown-{text:x}.elf'
    support.write_text(PROBE)
    subprocess.run([str(compiler), '-std=gnu11', '-O2', '-mthumb', '-fPIC',
        '-Wall', '-Wextra', '-Werror', '-fvisibility=hidden', '-fstack-protector-strong',
        '-nostdlib', '-static',
        f'-Wl,-Ttext={text:#x},-e,s3ce_finish_shutdown,--no-undefined',
        str(native/'shutdown_order.c'), str(support), '-o', str(output)], check=True)
    return output.read_bytes()


class ShutdownProof(Machine):
    def __init__(self, source, high, gpu_image=True):
        self.freed, self.methods, self.gpu_deleted = [], [], []
        self.hazard = None
        self.prefix_stop = None
        super().__init__(source, high)
        self.engine = self.zero(0x600)
        self.gpu_image = gpu_image
        self.boundary_order = []
        for offset in (0x33f74, 0xb14cc, 0x5c52c, 0x5ea50, 0xc3f44,
                       0xb0ce0, 0xafe68, 0xb06b0):
            self.hook(offset, self.record_method)
        self.hook(0xb0d2c, self.check_renderer)
        self.hook(0xeddd4, lambda o, a, s: self.ret(self.engine))
        self.hook(0xb5440, lambda o, a, s: self.ret(0))
        for offset in (0xa47dc, 0xa588c):
            self.hook(offset, self.gpu_delete)
        # These source calls remain in their original order. Their unrelated
        # subsystem state is outside the narrow image/renderer lifetime proof.
        for offset in (0x77f14, 0x84e94, 0xa6b9c, 0x35cac, 0x41184,
                       0x134644, 0xae9f8, 0x8a8e0, 0x83aac, 0x293a8,
                       0x2eb04, 0xae800):
            self.hook(offset, self.unrelated_cleanup)

    def memory_boundary(self, offset, args, sp):
        if offset in (0x132c9c, 0x132c94, 0x135910) and args[0]:
            self.freed.append(args[0])
        super().memory_boundary(offset, args, sp)

    def record_method(self, offset, args, sp):
        self.methods.append((offset, args[0]))

    def check_renderer(self, offset, args, sp):
        if args[0] not in self.active_allocations:
            self.hazard = dict(pc=hex(offset), renderer=hex(args[0]),
                               image=hex(self.vm.reg_read(UC_ARM_REG_R4)))
            self.vm.emu_stop()

    def gpu_delete(self, offset, args, sp):
        assert args[0] == self.gpu
        self.gpu_deleted.append((offset, args[0]))
        self.ret()

    def unrelated_cleanup(self, offset, args, sp):
        self.boundary_order.append(offset)
        self.ret()

    def prefix(self, start, end, args=(), extra=None):
        for register, value in zip(REGS, args):
            self.vm.reg_write(register, value)
        for register, value in (extra or {}).items():
            self.vm.reg_write(register, value)
        self.vm.reg_write(UC_ARM_REG_SP, self.stack_top)
        self.vm.reg_write(UC_ARM_REG_LR, self.stop)
        def stop(vm, pc, size, unused):
            vm.emu_stop()
        handle = self.vm.hook_add(UC_HOOK_CODE, stop,
                                  begin=self.code+end, end=self.code+end)
        self.vm.emu_start(self.code+start, self.stop, count=1000000)
        self.vm.hook_del(handle)
        assert self.vm.reg_read(UC_ARM_REG_PC) == self.code+end

    def prepare(self, gl2):
        c = self.code
        self.manager = self.allocate(0x88)
        assert self.call(0x5e7dc, (self.manager, 0)) == self.manager
        self.prefix(0x5c54c, 0x5c63c, (self.manager, 0, 0))
        self.pack = self.read(self.vm.reg_read(UC_ARM_REG_SP)+0x124)
        assert self.read(self.pack) == c+0x15f4b4
        self.image = self.allocate(0x38)
        self.prefix(0xb0bb4, 0xb0bfc, (self.image, 0))
        assert self.read(self.image) == c+0x160b60
        self.gpu = self.zero(0x40)
        if self.gpu_image:
            self.write(self.image+0x20, self.gpu)
        self.prefix(0x5a794, 0x5a804, (self.image,), {UC_ARM_REG_R6: self.pack})
        assert self.read(self.pack+0x90) == self.image and self.read(self.image+4) == 1
        vector = self.read(self.manager+0x3c)
        self.write(vector, self.pack)
        self.write(self.manager+0x38, 1)
        self.call(0xb285c, (self.pack,))
        manager_global = self.read(c+0x5c548)
        self.write(manager_global+0x14, self.manager)
        # Actual Display base constructor; original subclass vtable assignment
        # is the one at19998..199a0 in Display initialization. Canvas and
        # Graphics references are initially null in that constructor.
        self.display = self.allocate(0x28)
        self.call(0xb7f88, (self.display, 1920, 1080))
        self.write(self.display, c+0x160d28)
        self.renderer = self.zero(0x88)
        self.write(self.renderer, c+(0x1609c0 if gl2 else 0x160900))
        self.renderer_global = self.read(c+0x33fb4)
        self.write(self.renderer_global, self.display, self.renderer)
        framework_global = self.read(c+0x139048)
        self.write(framework_global+0x14, 0)  # Runtime graph is already closed.
        self.spyware = self.zero(8)
        self.write(self.spyware, c+0x15fd34)  # original EASpywareManager ctor store.
        self.write(framework_global+0x20, self.spyware)
        # Exercise the guarded main call, with its unrelated cache destructor
        # modeled at the explicit boundary rather than creating texture state.
        self.write(self.read(c+0x139360), 1)
        self.methods.clear()
        return self

    def main_cleanup(self):
        # Reproduce PUSH{r4-r11,lr} plus SUBsp,#0x44 at138c4c/50.
        v = self.vm
        integers = {r: 0x98760000+i*0x101 for i, r in enumerate(SAVED)}
        integers[UC_ARM_REG_R9] = 0  # source main's sb is its persistent zero.
        floats = {r: 0x1122334455660000+i for i, r in enumerate(FP_SAVED)}
        for register, value in (*integers.items(), *floats.items()):
            v.reg_write(register, value)
        frame = self.stack_top-0x44-9*4
        v.mem_write(frame, bytes(0x44))
        self.write(frame+0x44, *integers.values(), self.stop)
        guard = b'\xb9\x12\x73\xf0'*8
        v.mem_write(frame-0x8000, guard)
        v.mem_write(self.stack_top+0x80, guard)
        v.reg_write(UC_ARM_REG_SP, frame)
        v.reg_write(UC_ARM_REG_LR, self.stop)
        v.emu_start(self.code+0x139260, self.stop, count=1000000)
        if self.hazard:
            return False
        assert v.reg_read(UC_ARM_REG_PC) == self.stop
        assert v.reg_read(UC_ARM_REG_SP) == self.stack_top
        assert v.reg_read(UC_ARM_REG_R0) == 0
        assert all(v.reg_read(r) == x for r, x in integers.items())
        assert all(v.reg_read(r) == x for r, x in floats.items())
        assert bytes(v.mem_read(frame-0x8000, len(guard))) == guard
        assert bytes(v.mem_read(self.stack_top+0x80, len(guard))) == guard
        return True


def run_case(source, probe, high, gl2, gpu_image):
    old = ShutdownProof(source, high, gpu_image).prepare(gl2)
    completed = old.main_cleanup()
    assert completed == (not gpu_image)
    if gpu_image:
        assert old.hazard and old.renderer in old.freed
        assert old.read(old.renderer_global+4) == old.renderer
    p = ShutdownProof(source, high, gpu_image).prepare(gl2)
    load_elf(p.vm, probe, 0, set())
    symbols = symbol_table(probe)
    helper = symbols['s3ce_finish_shutdown'][0]
    patcher = symbols['s3ce_patch_shutdown_order'][0]
    assert helper & 1 and patcher & 1
    assert p.call(patcher, (p.code, p.code_length, p.code, EXTENT, helper), absolute=True) == 1
    assert p.call(patcher, (p.code, p.code_length, p.code, EXTENT, helper), absolute=True) == 2
    # Production's caller flushes the entire executable mapping after writes.
    p.vm.ctl_remove_cache(p.code, p.code+EXTENT)
    assert p.main_cleanup()
    assert p.gpu_deleted == ([(0xa588c if gl2 else 0xa47dc, p.gpu)] if gpu_image else [])
    assert all(p.freed.count(x) == 1 for x in
               (p.display, p.renderer, p.image, p.pack, p.manager, p.spyware))
    order = [x[0] for x in p.methods]
    assert order.index(0xb14cc) < order.index(0x5c52c) < order.index(0xb0ce0)
    assert order.index(0xb0ce0) < order.index(0xb06b0 if gl2 else 0xafe68)
    expected_boundaries = [
        0x77f14, 0x84e94, 0xa6b9c, 0x35cac, 0x41184, 0x134644, 0xae9f8,
        0x8a8e0, 0x83aac, 0x293a8, 0x2eb04, 0xae800]
    assert p.boundary_order == expected_boundaries
    if not gpu_image:
        assert p.boundary_order == old.boundary_order
    return dict(high=high, gl2=gl2, gpuImage=gpu_image, helper=hex(helper),
                originalHazard=old.hazard, repaired=True, gpuDeletes=len(p.gpu_deleted),
                displayDestroyedEarly=True, originalMainCleanupOrder=True,
                abiAndStackChecks=True, productionCompiledPatchAndHelper=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--ndk', type=Path,
        default=Path(os.environ['ANDROID_NDK_HOME']) if os.environ.get('ANDROID_NDK_HOME') else None)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.ndk is None:
        parser.error('--ndk or ANDROID_NDK_HOME is required')
    source = args.source.read_bytes()
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA
    result = []
    with tempfile.TemporaryDirectory(prefix='s3ce-shutdown-') as directory:
        for text in (0x21000000, 0xdb000000):
            probe = compile_probe(args.ndk, Path(directory), text)
            for high in (False, True):
                for gl2 in (False, True):
                    for gpu_image in (False, True):
                        result.append(run_case(source, probe, high, gl2, gpu_image))
    summary = dict(cases=len(result), passAll=True,
        scope='Original main cleanup and owning DLC/pack/image/Display/renderer methods; runtime graph already closed, uploaded GPU handle and parsed pack are inputs. Unrelated subsystem termination, filesystem lookup and GPU deletion are boundary models. Actual Android exit remains a separate acceptance gate.',
        results=result)
    if args.output:
        args.output.write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'results'}, indent=2))


if __name__ == '__main__':
    main()
