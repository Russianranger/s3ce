#!/usr/bin/env python3
"""Execute original SceneGame HUD selection with compiled production corrections.

The source's Display transforms, circle/rectangle tests, enable flags and route
selection execute. Only sound/click effects and final panel/game-mode endpoints
are modeled. This proves dispatch and neighboring bounds, not Android gameplay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from emulate_context_menu import Machine, PROBE, SOURCE_SHA, EXTENT, bits
from emulate_stack_bridge import load_elf, symbol_table

DIMENSIONS=((480,320,1.0),(960,640,2.0),(1920,1080,3.375),(1080,1920,3.375),(2160,1080,3.375))

def compile_probe(ndk, directory, text):
    native=Path(__file__).resolve().parents[1]
    support=directory/'support.c';support.write_text(PROBE)
    output=directory/f'hud-{text:x}.elf'
    compiler=ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi26-clang'
    subprocess.run([str(compiler),'-std=gnu11','-O2','-mthumb','-fPIC',
      '-Wall','-Wextra','-Werror','-fvisibility=hidden','-fstack-protector-strong',
      '-nostdlib','-static',f'-Wl,-Ttext={text:#x},-e,s3ce_patch_hud_input,--no-undefined',
      str(native/'hud_input.c'),str(support),'-o',str(output)],check=True)
    return output.read_bytes()

def run_case(source,probe,high,width,height,scale):
    p=Machine(source,high);v=p.vm;c=p.code
    scene,app,display,sim=[p.zero(0x2000)for _ in range(4)]
    p.write(scene+0x20,app);p.write(scene+0x24,sim)
    p.write(scene+0xa40,0x1e0);p.write(scene+0x1c0,6)
    p.write(app+8,width,height,0)
    p.write(display,bits(scale));p.write(display+0x20,width,height)
    p.write(p.relocate(0x166b2c),display);p.write(p.relocate(0x166bd4),app)
    # COW bounds from the hash-pinned original anim2d meshes172/173/174.
    # Their original925c4/92618 metric readers and130a60 width producer execute.
    sprites=p.zero(530*20);record=p.zero(20)
    p.write(record+8,sprites);p.write(app+0x114+0x88,record)
    for sprite,bounds in ((0x172,(-9,-24,9,24)),(0x173,(-.5,-24,.5,24)),(0x174,(-13,-24,13,24))):
        row=p.zero(20);data=p.zero(16);p.write(row+8,data)
        p.write(data,*map(bits,bounds));p.write(sprites+sprite*20+12,row)
    routes=[]
    def endpoint(offset,args,sp):
        if offset==0x12bb10:p.ret(7 if args[1]==0 else 0xffffffff)
        elif offset==0x12a328:p.ret(1234)
        elif offset==0x62580:p.ret(120)
        elif offset==0xc4368:p.ret(bits(0))
        elif offset==0x126df8:p.ret(max(width,height))
        elif offset==0x126e20:p.ret(min(width,height))
        elif offset in (0x12cc18,0x12b2f8):p.ret(0)
        elif offset==0x10e1d4:routes.append(('pause',args[1]));p.ret()
        elif offset==0x10dd14:routes.append(('buy',args[1]));p.ret()
        elif offset==0xffcec:routes.append(('panel',args[1]));p.ret()
        elif offset in (0xbf52c,0xbcacc,0x102430,0x1062ac):p.ret()
        else:raise AssertionError(hex(offset))
    for off in (0x12bb10,0x12a328,0x62580,0xc4368,0x126df8,0x126e20,0x12cc18,0x12b2f8,0x10e1d4,0x10dd14,
                0xffcec,0xbf52c,0xbcacc,0x102430,0x1062ac):p.hook(off,endpoint)
    assert p.call(0x130a60,(scene,))==45
    halfx=max(width,height)/2;halfy=min(width,height)/2
    def raw(logical):return tuple(round(h+(x-h)*scale)for x,h in zip(logical,(halfx,halfy)))
    pause=(p.call(0xae3c0,(display,34,2)),p.call(0xae458,(display,min(width,height)-34,2)))
    buy=(p.call(0xae3c0,(display,33,2)),p.call(0xae458,(display,min(width,height)-88,2)))
    plumbob=(p.call(0xae3c0,(display,max(width,height)-35,2)),pause[1])
    targets={
      'pause':(raw(pause),[('pause',0)]),
      'buy':(raw(buy),[('buy',13)]),
      'plumbob':(raw(plumbob),[('panel',3)]),
      'status':((round(150*scale),round(min(width,height)-24*scale)),[('panel',4)]),
      'wishes':((round(max(width,height)-140*scale),round(min(width,height)-24*scale)),[('panel',3)]),
      'mood_inner':((round(24*scale),round(70*scale)),[('mood',1)]),
      'mood_edge':((round(36*scale),round(70*scale)),[('mood',1)]),
      'mood_outside':((round(48*scale),round(70*scale)),[]),
      'world_gap':((round(halfx),round(min(width,height)-80*scale)),[]),
    }
    def tap(point):
        routes.clear();p.write(scene+0x1c0,6);v.mem_write(scene+0x660,b'\0');v.mem_write(scene+0x21c,b'\0')
        try:handled=p.call(0x107254,(scene,*point,0))
        except Exception:
            from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1
            print('FAILED',width,height,scale,point,hex(v.reg_read(UC_ARM_REG_PC)-c),hex(v.reg_read(UC_ARM_REG_R0)),hex(v.reg_read(UC_ARM_REG_R1)))
            raise
        if v.mem_read(scene+0x21c,1)[0]:routes.append(('mood',1))
        return list(routes),handled
    original={k:tap(point)for k,(point,_)in targets.items()}
    load_elf(v,probe,0,set());symbols=symbol_table(probe);patch=symbols['s3ce_patch_hud_input'][0];gateway=symbols['s3ce_hud_status_width_gateway'][0]
    before=bytes(v.mem_read(c,EXTENT))
    assert p.call(patch,(c,0x200000,c,EXTENT,gateway),absolute=True)==1
    after=bytes(v.mem_read(c,EXTENT))
    changed=[i for i,(a,b)in enumerate(zip(before,after))if a!=b]
    assert all(any(t<=i<t+4 for t in (0x1073cc,0x107500,0x1075e0,0x1077e0,0x107844,0x107848,0x10784c))for i in changed)
    assert p.call(patch,(c,0x200000,c,EXTENT,gateway),absolute=True)==2
    corrected={k:tap(point)for k,(point,_)in targets.items()}
    for k,(_,expected)in targets.items():assert corrected[k][0]==expected,(width,height,scale,k,targets[k],original[k],corrected[k])
    if scale==1:assert original==corrected
    if scale==3.375:
        assert original['buy'][0]==[('pause',0)]
        assert original['wishes'][0]==[]
        assert original['mood_inner'][0]==[]
        assert original['mood_edge'][0]==[]
    return dict(high=high,width=width,height=height,scale=scale,
      targets={k:list(v[0])for k,v in targets.items()},original=original,corrected=corrected,
      compiledProductionPatch=True,originalDisplayAndHitTests=True,abiAndStackChecks=True,
      boundary='Final panel/game-mode endpoints and sound/click effects are modeled')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--ndk',type=Path,default=os.environ.get('ANDROID_NDK_HOME'));ap.add_argument('--output',type=Path)
    a=ap.parse_args();assert a.ndk,'--ndk required';source=a.source.read_bytes();assert hashlib.sha256(source).hexdigest()==SOURCE_SHA
    results=[]
    with tempfile.TemporaryDirectory(prefix='s3ce-hud-')as d:
        for text in (0x21000000,0xdb000000):
            probe=compile_probe(a.ndk,Path(d),text)
            for high in (False,True):
                for dims in DIMENSIONS:results.append(run_case(source,probe,high,*dims))
    summary=dict(cases=len(results),dispatchChecks=len(results)*9,passAll=True,results=results)
    if a.output:a.output.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items()if k!='results'},indent=2))
if __name__=='__main__':main()
