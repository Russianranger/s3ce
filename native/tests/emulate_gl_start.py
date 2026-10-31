#!/usr/bin/env python3
"""Execute the source runtime's actual ARM32 Thumb JNI dispatch with mock JNI.
Requires unicorn==2.1.4; source ELF remains user-supplied. No Android code is emulated.
"""
import argparse
import hashlib
import struct
import zipfile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3

BASE, AUX, STACK = 0x10000000, 0x20000000, 0x30000000
ELF_SHA = 'd93bc59497d377a9524aa8b3fa090aec0e32048bec4bb5e50b757c2f7234befe'

def word(vm, address, value=None):
    if value is None:
        return struct.unpack('<I', vm.mem_read(address, 4))[0]
    vm.mem_write(address, struct.pack('<I', value))

def cstring(vm, address):
    result = bytearray()
    while True:
        value = vm.mem_read(address, 1)[0]
        if not value:
            return result.decode('ascii')
        result.append(value)
        address += 1

def machine(data):
    vm = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    vm.mem_map(BASE, 0x60000)
    vm.mem_map(AUX, 0x10000)
    vm.mem_map(STACK, 0x10000)
    header = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    for i in range(header[10]):
        p = struct.unpack_from('<IIIIIIII', data, header[5] + i*header[9])
        if p[0] == 1:
            vm.mem_write(BASE + p[2], data[p[1]:p[1]+p[4]])
    for i in range(header[12]):
        section = struct.unpack_from('<IIIIIIIIII', data, header[6] + i*header[11])
        if section[1] != 9:  # SHT_REL
            continue
        for at in range(section[4], section[4]+section[5], section[9]):
            offset, info = struct.unpack_from('<II', data, at)
            if info & 0xff == 23:  # R_ARM_RELATIVE
                word(vm, BASE+offset, (word(vm, BASE+offset)+BASE) & 0xffffffff)
    return vm

def run(data, version, inject_exception=False):
    vm = machine(data)
    env, table = AUX+0x1000, AUX+0x2000
    thread, view = 0x12345678, 0x44332211
    thread_class, view_class = 0x11110001, 0x22220002
    addresses = {0x54:AUX+0x100, 0x58:AUX+0x120, 0x7c:AUX+0x140,
                 0x84:AUX+0x160, 0xf8:AUX+0x180, 0x3c:AUX+0x1a0,
                 0x40:AUX+0x1c0, 0x44:AUX+0x1e0}
    for offset, address in addresses.items():
        vm.mem_write(address, b'\x70\x47')  # BX LR, after instrumentation hook
        word(vm, table+offset, address|1)
    word(vm, env, table)
    lookups, calls = [], []
    exception = {'pending':False, 'describe':0, 'clear':0,
                 'debug_message':0, 'debug_break_check':0}
    stop = AUX+0xff0
    vm.mem_write(stop, b'\x70\x47')

    def hook(cpu, address, size, unused):
        if address == addresses[0x54]:
            cpu.reg_write(UC_ARM_REG_R0, cpu.reg_read(UC_ARM_REG_R1))
        elif address == addresses[0x7c]:
            obj = cpu.reg_read(UC_ARM_REG_R1)
            cpu.reg_write(UC_ARM_REG_R0, thread_class if obj == thread else view_class)
        elif address == addresses[0x84]:
            row = {'class':cpu.reg_read(UC_ARM_REG_R1),
                   'name':cstring(cpu, cpu.reg_read(UC_ARM_REG_R2)),
                   'signature':cstring(cpu, cpu.reg_read(UC_ARM_REG_R3)),
                   'id':0x88000000+len(lookups)*4}
            lookups.append(row)
            cpu.reg_write(UC_ARM_REG_R0, row['id'])
        elif address == addresses[0xf8]:
            args = [cpu.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
            calls.append((args[:3], word(cpu,args[3])))
            exception['pending'] = inject_exception
            cpu.reg_write(UC_ARM_REG_R0, 0)
        elif address == addresses[0x3c]:  # ExceptionOccurred
            cpu.reg_write(UC_ARM_REG_R0, 0xface0001 if exception['pending'] else 0)
        elif address == addresses[0x40]:  # ExceptionDescribe
            assert exception['pending']
            exception['describe'] += 1
        elif address == addresses[0x44]:  # ExceptionClear
            exception['clear'] += 1
            exception['pending'] = False
        elif address in [BASE+0x1b148, BASE+0x2b9ec]:
            # Skip the original optional debug logger/break-policy helpers.
            # Returning zero from the latter avoids its intentional fault.
            key = 'debug_message' if address == BASE+0x1b148 else 'debug_break_check'
            exception[key] += 1
            cpu.reg_write(UC_ARM_REG_R0, 0)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
        elif address in [BASE+0x217e6, stop]:
            cpu.emu_stop()
    vm.hook_add(UC_HOOK_CODE, hook)
    for reg, value in [(UC_ARM_REG_R0,env),(UC_ARM_REG_R1,thread),(UC_ARM_REG_R2,view),
                       (UC_ARM_REG_SP,STACK+0x8000)]:
        vm.reg_write(reg,value)
    vm.emu_start(BASE+0x21651,0,count=5000)  # real setViewNative through glInit cache store
    cached = word(vm, BASE+0x53af0+0x14)
    assert lookups[-1] == {'class':thread_class,'name':'glInit','signature':'(I)V','id':cached}
    assert word(vm,BASE+0x53af0+8) == thread
    assert word(vm,BASE+0x53af0+4) == view
    word(vm,BASE+0x53af0,env)
    word(vm,BASE+0x55a04,version)
    vm.mem_write(BASE+0x55a04+8,b'\x01')  # cache already valid; avoid unrelated version parser
    vm.reg_write(UC_ARM_REG_SP,STACK+0x8000)
    vm.reg_write(UC_ARM_REG_LR,stop|1)
    vm.emu_start(BASE+0x210a5,0,count=5000)  # real s3eGL_start and callMethod
    assert vm.reg_read(UC_ARM_REG_PC) == stop
    assert calls == [([env,thread,cached], 1 if version <= 0x1ff else 2)], calls
    assert exception['pending'] is False
    expected_events = 1 if inject_exception else 0
    for key in ['describe', 'clear', 'debug_message', 'debug_break_check']:
        assert exception[key] == expected_events, (key, exception)
    if inject_exception:
        print(f"PASS injected Java glInit exception: real Thumb callMethod invoked "
              f"ExceptionOccurred/Describe/Clear and debug handlers; pending=0; "
              f"s3eGL_start {version:#x} returned normally")
    print(f'PASS real Thumb setViewNative cached glInit(I)V; s3eGL_start {version:#x} -> CallVoidMethodV(env,thread,id,int={calls[0][1]})')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source',help='Original APK or original libairplay.so')
    args=parser.parse_args()
    if zipfile.is_zipfile(args.source):
        with zipfile.ZipFile(args.source) as apk:
            data=apk.read('lib/armeabi/libairplay.so')
    else:
        with open(args.source,'rb') as source:
            data=source.read()
    assert hashlib.sha256(data).hexdigest() == ELF_SHA
    run(data,0x101)
    run(data,0x200)
    run(data,0x101,inject_exception=True)
    run(data,0x200,inject_exception=True)
