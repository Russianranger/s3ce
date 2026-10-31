#!/usr/bin/env python3
"""Execute the original UI scale/camera code and reproduce its depth clipping.

Requires Unicorn 2.1.4 and the separately unpacked, SHA-pinned source game.
The ARM test executes the original Display constructor, applyScale, paired
input/render coordinate transforms, orthographic-camera setter and projection
builder. Only platform-property and GL driver boundaries are modeled. The
candidate changes one ARM instruction: the Z argument of this UI scale becomes
1.0, while the original X/Y scale and input transforms remain unchanged.

Optional --anim2d/--atlas/--report arguments replay real source sprite arrays,
RGBA pixels, and captured live GL matrices in a host fixed-function GL context.
That replay proves clipping/pixels, not the complete Android app or progression
past Create-a-Sim. No APK is built or published by this test.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
import zlib

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
from game_pointer_fixture import GamePointerFixture, CODE_EXTENT, PREFERRED, SOURCE_SHA

PATCH_OFFSET = 0x135d80
ENTRY_OFFSET = 0xae1b0
ORIGINAL = bytes.fromhex('0020a0e1')  # MOV r2,r0
REPLACEMENT = bytes.fromhex('fe25a0e3')  # MOV r2,#0x3f800000 (float1)
SCALE_BEGIN, SCALE_END = 0xae180, 0xae1bc
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
SAVED = tuple(range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1))
ANIM_SHA = 'd2cd083b6cdb5132a3de8dee171526b91d28894d8742c001ab2b77e06438b779'
ATLAS_SHA = '6f3165db6cb5c94cdd403594e71bf88b4fe772a539f0ad3dbb147a837e7c6b6e'


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def value(word):
    return struct.unpack('<f', struct.pack('<I', word))[0]


class SourceProof:
    def __init__(self, source, layout, dimensions, variant):
        self.vm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        base, data, heap, self.stack = layout
        self.fixture = f = GamePointerFixture(self.vm, source, base, heap, data)
        self.base, self.dimensions = base, dimensions
        self.vm.mem_map(self.stack, 0x10000)
        self.stop, self.sp = self.stack + 0xff00, self.stack + 0xe000
        self.scales = []
        self.gl_calls = []
        self.matrix_mode = 0x1700
        self.matrices = {mode:identity() for mode in (0x1700,0x1701,0x1702)}
        self.matrix_stacks = {mode:[] for mode in self.matrices}
        assert bytes(self.vm.mem_read(base + PATCH_OFFSET, 4)) == ORIGINAL
        # Exactly the reached Display graphics-singleton pool is relocated.
        original = f.read(base + 0xae1bc)
        assert original == PREFERRED + 0x166b2c
        slot = data + original - PREFERRED - CODE_EXTENT
        f.write(base + 0xae1bc, slot)
        f.write(slot, f.display)
        for literal in (0xae340,0x135dc4,0x135dec):
            assert f.read(base+literal) == original
            f.write(base+literal,slot)
        # Original camera's identity-matrix template, reached by mode0x31.
        assert f.read(base + 0x1262f4) == PREFERRED + 0x158d7c
        f.write(base + 0x1262f4, base + 0x158d7c)
        if variant in ('entry','both'):
            self.vm.mem_write(base + ENTRY_OFFSET, REPLACEMENT)
        if variant in ('projection','both'):
            self.vm.mem_write(base + PATCH_OFFSET, REPLACEMENT)
        self.vm.hook_add(UC_HOOK_CODE, self.hook)

    def hook(self, cpu, address, size, unused):
        offset = address - self.base
        if offset == 0x3e8:
            cpu.reg_write(UC_ARM_REG_R0, 4)  # Shipped Android platform ID.
        elif offset == 0x500:
            prop = cpu.reg_read(UC_ARM_REG_R0)
            assert prop in (4, 5, 11)
            cpu.reg_write(UC_ARM_REG_R0, {4:self.dimensions[0], 5:self.dimensions[1], 11:0}[prop])
        elif offset in (0x5c,0x60,0x64,0x23c,0x260,0x264,0x274,0x27c):
            args = tuple(cpu.reg_read(r) for r in REGS)
            self.gl_calls.append((offset,args))
            if offset == 0x64:
                assert args[0] in self.matrices
                self.matrix_mode = args[0]
            elif offset == 0x5c:
                self.matrices[self.matrix_mode] = identity()
            elif offset == 0x60:
                self.matrices[self.matrix_mode] = list(struct.unpack('<16f',cpu.mem_read(args[0],64)))
            elif offset == 0x23c:
                matrix = list(struct.unpack('<16f',cpu.mem_read(args[0],64)))
                self.matrices[self.matrix_mode] = multiply(self.matrices[self.matrix_mode],matrix)
            elif offset == 0x264:
                self.matrix_stacks[self.matrix_mode].append(self.matrices[self.matrix_mode][:])
            elif offset == 0x260:
                self.matrices[self.matrix_mode] = self.matrix_stacks[self.matrix_mode].pop()
            elif offset == 0x274:
                angle,x,y,z = [value(a)for a in args]
                assert (x,y,z)==(0,0,1)
                c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
                rotation=[c,s,0,0,-s,c,0,0,0,0,1,0,0,0,0,1]
                self.matrices[self.matrix_mode] = multiply(self.matrices[self.matrix_mode],rotation)
            else:
                self.scales.append(args[:3])
                scale = identity()
                scale[0],scale[5],scale[10] = [value(a)for a in args[:3]]
                self.matrices[self.matrix_mode] = multiply(self.matrices[self.matrix_mode],scale)
        else:
            return
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    def call(self, offset, args=(), stack_args=()):
        f = self.fixture
        for reg, arg in zip(REGS, args):
            self.vm.reg_write(reg, arg)
        sentinel = {reg:0x31415900 + i for i, reg in enumerate(SAVED)}
        for reg, arg in sentinel.items():
            self.vm.reg_write(reg, arg)
        f.write(self.sp, *stack_args)
        self.vm.reg_write(UC_ARM_REG_SP, self.sp)
        self.vm.reg_write(UC_ARM_REG_LR, self.stop)
        self.vm.emu_start(self.base + offset, self.stop, count=200000)
        assert self.vm.reg_read(UC_ARM_REG_PC) == self.stop
        assert self.vm.reg_read(UC_ARM_REG_SP) == self.sp
        assert all(self.vm.reg_read(reg) == arg for reg, arg in sentinel.items())

    def run(self):
        f = self.fixture
        self.call(0xae810, [f.display])
        scale = f.read(f.display)
        points = []
        point = f.allocate()
        width, height = self.dimensions
        for x, y in ((0,0), (width//2,height//2), (width-1,height-1),
                     (width*3//4,height*2//3)):
            f.write(point, x, y)
            self.call(0xae4f0, [f.display, point, point+4])
            transformed = (f.read(point), f.read(point+4))
            self.call(0xae5a0, [f.display, point, point+4])
            rendered = (f.read(point), f.read(point+4))
            points.append((x,y,transformed,rendered))
        # Execute original camera setter and original orthographic builder.
        camera = f.allocate(0x200)
        self.call(0xa78b8, [camera, bits(float(max(width,height))),
                  bits(min(width,height)/max(width,height)), bits(-100.0)], [bits(100.0)])
        self.call(0x12612c, [camera])
        camera_projection = list(struct.unpack('<16f', self.vm.mem_read(camera+0xf8,64)))
        assert abs(camera_projection[10] + .01) < 1e-8
        def load_projection():
            self.call(0x135dcc,[0x1701])
            self.call(0x135d50,[camera+0xf8])
            return self.matrices[0x1701][:]
        assert f.read(f.display+8)==bits(1)
        before = load_projection()
        self.call(SCALE_BEGIN, [f.display])
        assert f.read(f.display+8) == scale
        entry_scale = self.scales[-1]
        during = load_projection()
        projection_scale = self.scales[-1]
        self.call(0xae30c,[f.display])
        assert f.read(f.display+8)==bits(1)
        after = load_projection()
        return dict(scale=value(scale),entry_scale=list(entry_scale),
                    projection_scale=list(projection_scale),points=points,
                    before=before,during=during,after=after,
                    camera_projection=camera_projection)


def identity():
    return [1.0 if i%5==0 else 0.0 for i in range(16)]


def multiply(a,b):
    return [sum(a[k*4+r]*b[c*4+k] for k in range(4))
            for c in range(4) for r in range(4)]


def arm_proof(source):
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA
    # Link this instruction-level proof to the production helper's exact
    # fingerprint/replacement bytes. Native host tests execute the helper;
    # this parser does not claim to execute compiled production C here.
    helper=(Path(__file__).resolve().parents[1]/'ui_depth.c').read_text()
    guards={}
    for name in ('original_scale','z_one'):
        match=re.search(r'\b'+name+r'\[\]\s*=\s*\{([^}]+)\}',helper)
        assert match, name
        guards[name]=bytes(int(x,16)for x in re.findall(r'0x([0-9a-fA-F]{2})\b',match.group(1)))
    assert guards['original_scale']==source[0xd2a0+0x135d50:0xd2a0+0x135dc4]
    assert guards['z_one']==REPLACEMENT
    assert re.search(r'#define\s+PROJECTION_LOAD\s+0x135d50u',helper)
    assert re.search(r'#define\s+Z_ARGUMENT\s+0x30u',helper)
    for offset in (PATCH_OFFSET,ENTRY_OFFSET):
        assert source[0xd2a0+offset:0xd2a0+offset+4] == ORIGINAL
    layouts = ((0x4a000000,0x68000000,0x60000000,0x70000000),
               (0xc0cb8000,0xd1000000,0xbfc00000,0xe0000000))
    results = []
    for layout in layouts:
        for dimensions in ((480,320),(1280,720),(1920,1080),(2560,1440)):
            variants = {variant:SourceProof(source,layout,dimensions,variant).run()
                        for variant in ('original','entry','projection','both')}
            old,new = variants['original'],variants['projection']
            for variant,result in variants.items():
                assert result['scale']==old['scale']
                assert result['points']==old['points']
                assert result['before']==old['before']==result['after']
                assert result['during'][:10]==old['during'][:10]
                assert result['during'][11:]==old['during'][11:]
            assert variants['entry']['during']==old['during'], 'entry-only patch must fail to repair downstream projection'
            assert variants['both']['during']==new['during']
            assert old['entry_scale']==[bits(old['scale'])]*3
            assert old['projection_scale']==[bits(old['scale'])]*3
            assert new['entry_scale']==old['entry_scale']
            assert new['projection_scale']==[bits(old['scale']),bits(old['scale']),bits(1)]
            z = -50
            old_ndc = old['during'][10]*z
            new_ndc = new['during'][10]*z
            assert abs(new_ndc-.5)<1e-7
            assert (abs(old_ndc)>1)==(old['scale']>2)
            results.append(dict(code=hex(layout[0]),dimensions=dimensions,
                scale=old['scale'],source_projection_scale=[value(x)for x in old['projection_scale']],
                fixed_projection_scale=[value(x)for x in new['projection_scale']],
                original_projection=old['during'],fixed_projection=new['during'],
                original_ndc_z=old_ndc,fixed_ndc_z=new_ndc,input_unchanged=True,
                entry_only_does_not_fix=True,outside_display_bracket_unchanged=True))
    return results


def read_objects(path):
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ANIM_SHA
    assert data[:12] == b'\xabJSR184\xbb\r\n\x1a\n'
    cursor, result = 12, {}
    while cursor < len(data):
        compression, total, raw_size = struct.unpack_from('<BII',data,cursor)
        assert compression == 0 and total == raw_size+13
        end = cursor+total
        assert zlib.adler32(data[cursor:end-4]) == struct.unpack_from('<I',data,end-4)[0]
        pos = cursor+9
        while pos < end-4:
            kind, size = struct.unpack_from('<BI',data,pos)
            body = data[pos+5:pos+5+size]
            assert len(body) == size
            result[len(result)+1] = (kind,body)
            pos += 5+size
        assert pos == end-4
        cursor = end
    assert cursor == len(data) and len(result) == 2500
    return result


def mesh(objects, sprite):
    kind,b = next((kind,b) for kind,b in objects.values()
                  if kind == 14 and struct.unpack_from('<I',b)[0] == 1000+sprite)
    kind,vb = objects[struct.unpack_from('<I',b,62)[0]]
    assert kind == 21
    pos_ref = struct.unpack_from('<I',vb,16)[0]
    uv_ref = struct.unpack_from('<I',vb,48)[0]
    pos_bias = struct.unpack_from('<3f',vb,20)
    pos_scale = struct.unpack_from('<f',vb,32)[0]
    uv_bias = struct.unpack_from('<3f',vb,52)
    uv_scale = struct.unpack_from('<f',vb,64)[0]
    assert pos_bias == uv_bias == (0,0,0) and pos_scale == .5 and uv_scale == 1/1024
    def array(ref, components):
        kind,b = objects[ref]
        assert kind == 20 and b[12:15] == bytes([2,components,0])
        count = struct.unpack_from('<H',b,15)[0]
        assert count == 4
        return struct.unpack_from('<'+'h'*(count*components),b,17)
    pos,uv = array(pos_ref,3),array(uv_ref,2)
    assert pos[2::3] == (0,0,0,0)
    return pos,uv


def captured_matrices(report, number=8192):
    text = report.read_text()
    result = {}
    for label in ('projection','modelview','texture'):
        m = re.search(rf'^UI GPU #{number} {label}=([^\r\n]+)$',text,re.M)
        assert m, (number,label)
        result[label] = [float(x) for x in m.group(1).replace(';',',').split(',')]
        assert len(result[label]) == 16
    assert abs(result['projection'][10]+.03375) < 1e-7
    assert -51 < result['modelview'][14] < -45
    return result


def pixel_proof(anim2d, atlas, report, output):
    # Host renderer code is independent of the ARM instruction/GL-query capture.
    # Only the driver's desktop fixed-function equivalent is used for playback.
    from PIL import Image
    objects = read_objects(anim2d)
    image = Image.open(atlas).convert('RGBA')
    assert image.size == (512,512) and hashlib.sha256(image.tobytes()).hexdigest() == ATLAS_SHA
    captured = captured_matrices(report)
    # Reuse the small host EGL context for binding creation only. It has no
    # game matrices or rendering decisions; all relevant state is set below.
    # This loader keeps the test usable without any analysis-directory modules.
    E = C.CDLL('libEGL.so.1')
    I,U,F,P = C.c_int,C.c_uint,C.c_float,C.c_void_p
    E.eglGetProcAddress.argtypes=[C.c_char_p];E.eglGetProcAddress.restype=P
    platform=C.CFUNCTYPE(P,U,P,C.POINTER(I))(E.eglGetProcAddress(b'eglGetPlatformDisplayEXT'))
    display=platform(0x31dd,None,None)
    E.eglInitialize.argtypes=[P,C.POINTER(I),C.POINTER(I)];E.eglInitialize.restype=I
    a,b=I(),I();assert E.eglInitialize(display,C.byref(a),C.byref(b))
    E.eglBindAPI.argtypes=[U];E.eglBindAPI.restype=I;assert E.eglBindAPI(0x30a2)
    config=P();count=I();attrs=(I*13)(0x3033,1,0x3040,8,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038)
    E.eglChooseConfig.argtypes=[P,C.POINTER(I),C.POINTER(P),I,C.POINTER(I)];E.eglChooseConfig.restype=I
    assert E.eglChooseConfig(display,attrs,C.byref(config),1,C.byref(count)) and count.value
    E.eglCreateContext.argtypes=[P,P,P,C.POINTER(I)];E.eglCreateContext.restype=P
    context=E.eglCreateContext(display,config,None,(I*1)(0x3038));assert context
    E.eglCreatePbufferSurface.argtypes=[P,P,C.POINTER(I)];E.eglCreatePbufferSurface.restype=P
    width,height=1920,1080
    surface=E.eglCreatePbufferSurface(display,config,(I*5)(0x3057,width,0x3056,height,0x3038));assert surface
    E.eglMakeCurrent.argtypes=[P,P,P,P];E.eglMakeCurrent.restype=I
    assert E.eglMakeCurrent(display,surface,surface,context)
    def proc(name, restype, *args):
        return C.CFUNCTYPE(restype,*args)(E.eglGetProcAddress(name.encode()))
    viewport=proc('glViewport',None,I,I,I,I)
    matrix_mode=proc('glMatrixMode',None,U);load_matrix=proc('glLoadMatrixf',None,P)
    clear_color=proc('glClearColor',None,F,F,F,F);clear=proc('glClear',None,U)
    enable=proc('glEnable',None,U);disable=proc('glDisable',None,U)
    enable_array=proc('glEnableClientState',None,U);disable_array=proc('glDisableClientState',None,U)
    blend=proc('glBlendFunc',None,U,U);color=proc('glColor4f',None,F,F,F,F)
    gen=proc('glGenTextures',None,I,C.POINTER(U));bind=proc('glBindTexture',None,U,U)
    parameter=proc('glTexParameteri',None,U,U,I);pixel_store=proc('glPixelStorei',None,U,I)
    tex_image=proc('glTexImage2D',None,U,I,I,I,I,I,U,U,P)
    vertex=proc('glVertexPointer',None,I,U,I,P);texcoord=proc('glTexCoordPointer',None,I,U,I,P)
    draw_arrays=proc('glDrawArrays',None,U,I,I);draw_elements=proc('glDrawElements',None,U,I,U,P)
    read=proc('glReadPixels',None,I,I,I,I,U,U,P);finish=proc('glFinish',None)
    get_error=proc('glGetError',U)
    texture=U();gen(1,C.byref(texture));bind(0xde1,texture.value)
    pixel_store(0xcf5,1);pixel_store(0xd05,1)
    parameter(0xde1,0x2800,0x2601);parameter(0xde1,0x2801,0x2701)
    parameter(0xde1,0x2802,0x812f);parameter(0xde1,0x2803,0x812f)
    # The source RGBA mip generator's integer box mean was independently
    # instruction-tested. Recreate complete levels here so the live MIN filter
    # is retained; these magnified sprites use exact, unmodified source level0.
    level,width_level,height_level,level_bytes=0,512,512,image.tobytes()
    while True:
        raw=C.create_string_buffer(level_bytes)
        tex_image(0xde1,level,0x1908,width_level,height_level,0,0x1908,0x1401,raw)
        if (width_level,height_level)==(1,1):break
        w,h=max(1,width_level//2),max(1,height_level//2)
        reduced=bytearray(w*h*4)
        for y in range(h):
            for x in range(w):
                for component in range(4):
                    reduced[(y*w+x)*4+component]=sum(
                        level_bytes[((y*2+dy)*width_level+x*2+dx)*4+component]
                        for dy in range(2) for dx in range(2))//4
        level,width_level,height_level,level_bytes=level+1,w,h,bytes(reduced)
    viewport(0,0,width,height)
    for cap in (0xb71,0xb44,0xc11,0xbc0,0xb50):disable(cap)
    enable(0xde1);enable(0xbe2);blend(0x302,0x303);color(1,1,1,1)
    enable_array(0x8074);enable_array(0x8078);disable_array(0x8076)
    result=[]
    try:
        for sprite in (96,99,119,122):
            pos,uv=mesh(objects,sprite)
            vp=(C.c_short*len(pos))(*pos);tp=(C.c_short*len(uv))(*uv)
            vertex(3,0x1402,0,C.cast(vp,P));texcoord(2,0x1402,0,C.cast(tp,P))
            renders={}
            for fixed in (False,True):
                projection=captured['projection'][:]
                if fixed:projection[10] /= 3.375
                for kind,name in ((0x1701,'projection'),(0x1700,'modelview'),(0x1702,'texture')):
                    matrix_mode(kind)
                    values=projection if name=='projection' else captured[name]
                    matrix=(F*16)(*values);load_matrix(C.cast(matrix,P))
                clear_color(.25,.25,.25,1);clear(0x4000)
                draw_arrays(5,0,4);finish()
                pixels=(C.c_ubyte*(width*height*4))();read(0,0,width,height,0x1908,0x1401,pixels)
                assert get_error()==0
                data=bytes(pixels);changed=sum(data[i:i+3]!=b'@@@' for i in range(0,len(data),4))
                if fixed:assert changed>50,(sprite,changed)
                else:assert changed==0,(sprite,changed)
                renders[fixed]=data
                result.append(dict(sprite=sprite,fixed=fixed,changed_pixels=changed,
                    ndc_z=projection[10]*captured['modelview'][14],sha256=hashlib.sha256(data).hexdigest()))
                if output:
                    output.mkdir(parents=True,exist_ok=True)
                    Image.frombytes('RGBA',(width,height),data).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(output/(f'ui-{sprite}-'+('fixed'if fixed else 'clipped')+'.png'))
            # Index representation alone cannot remove this clipping condition.
            projection=captured['projection'][:]
            matrix_mode(0x1701);m=(F*16)(*projection);load_matrix(C.cast(m,P))
            clear_color(.25,.25,.25,1);clear(0x4000)
            indices=(C.c_ushort*4)(0,1,2,3)
            draw_elements(5,4,0x1403,C.cast(indices,P));finish()
            pixels=(C.c_ubyte*(width*height*4))();read(0,0,width,height,0x1908,0x1401,pixels)
            assert bytes(pixels)==renders[False] and get_error()==0
    finally:
        E.eglMakeCurrent(display,None,None,None)
        E.eglDestroySurface.argtypes=[P,P];E.eglDestroyContext.argtypes=[P,P];E.eglTerminate.argtypes=[P]
        E.eglDestroySurface(display,surface);E.eglDestroyContext(display,context);E.eglTerminate(display)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--anim2d',type=Path)
    parser.add_argument('--atlas',type=Path)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    source=args.source.read_bytes()
    results={'arm':arm_proof(source),'modeled_boundaries':['platform properties','GL driver calls']}
    if args.anim2d or args.atlas or args.report:
        if not (args.anim2d and args.atlas and args.report):
            parser.error('--anim2d, --atlas and --report must be provided together')
        results['pixels']=pixel_proof(args.anim2d,args.atlas,args.report,args.output)
    print(json.dumps(results,indent=2))
    print('PASS original ARM XY-preserving UI depth correction; pixel replay is optional, not an Android-app progression test.')


if __name__=='__main__':main()
