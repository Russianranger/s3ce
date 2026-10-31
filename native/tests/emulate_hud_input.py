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
import struct
from unicorn.arm_const import UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_PC, UC_ARM_REG_SP
from emulate_context_menu import Machine, PROBE, SOURCE_SHA, EXTENT, bits, SAVED
from emulate_stack_bridge import load_elf, symbol_table

DIMENSIONS=((480,320,1.0),(960,640,2.0),(1920,1080,3.375),(1080,1920,3.375),(2160,1080,3.375))

def compile_probe(ndk, directory, text):
    native=Path(__file__).resolve().parents[1]
    support=directory/'support.c';support.write_text(PROBE+r"""
/* Reproduce the original camera render tail's caller-owned prologue. The tail
 * has its own matching pop; this wrapper only supplies scene/renderer registers. */
__attribute__((naked,target("arm"))) void render_camera_tail(void){
 __asm__ volatile("push {r3-r7,lr}\nmov r4,r0\nmov r5,r1\nbx r2\n");
}
""")
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
    renderer=p.zero(64);vtable=p.zero(128);p.write(renderer,vtable)
    p.write(vtable+0x34,c+0x358)
    # Distinct draw handles only. Original draw boundary selects26c/270.
    p.write(scene+0x26c,0x12223344,0x56667788)
    event,outer,event_data=[p.zero(64)for _ in range(3)]
    p.write(event+12,outer);p.write(outer+8,event_data)
    routes=[];draws=[];force_passes=[]
    def endpoint(offset,args,sp):
        if offset==0x358:
            draws.append((args[1],args[2],args[3],p.read(sp)));p.ret()
        elif offset==0x107254:force_passes.append(args[3])
        elif offset==0x1040a4:
            # World lookup/dispatch is outside this HUD proof. Retire the exact
            # original104014 frame only after both original HUD passes decline.
            routes.append(('world',0))
            saved=struct.unpack('<9I',v.mem_read(sp+0x34,36))
            for reg,value in zip(SAVED,saved):v.reg_write(reg,value)
            v.reg_write(UC_ARM_REG_SP,sp+0x58);v.reg_write(UC_ARM_REG_PC,saved[-1])
        elif offset==0x12bb10:p.ret(7 if args[1]==0 else 0xffffffff)
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
    for off in (0x358,0x107254,0x1040a4,0x12bb10,0x12a328,0x62580,0xc4368,0x126df8,0x126e20,0x12cc18,0x12b2f8,0x10e1d4,0x10dd14,
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
    def tap(point,camera_enabled=False,expanded=False,force=0,phase=6,dispatcher=False):
        routes.clear();force_passes.clear();p.write(scene+0x1c0,phase)
        p.write(scene+0xa40,0x1e0 | (0x2000 if camera_enabled else 0))
        v.mem_write(scene+0x660,b'\0');v.mem_write(scene+0x21c,b'\0')
        v.mem_write(scene+0x26a,bytes((int(expanded),)))
        p.write(event_data+4,*point)
        try:handled=(p.call(0x104014,(scene,event)) if dispatcher else
                     p.call(0x107254,(scene,*point,force)))
        except Exception:
            from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1
            print('FAILED',width,height,scale,point,hex(v.reg_read(UC_ARM_REG_PC)-c),hex(v.reg_read(UC_ARM_REG_R0)),hex(v.reg_read(UC_ARM_REG_R1)))
            raise
        if v.mem_read(scene+0x26a,1)[0]!=int(expanded):routes.append(('camera',1-int(expanded)))
        if v.mem_read(scene+0x21c,1)[0]:routes.append(('mood',1))
        return list(routes),handled
    original={k:tap(point)for k,(point,_)in targets.items()}
    load_elf(v,probe,0,set());symbols=symbol_table(probe);patch=symbols['s3ce_patch_hud_input'][0];gateway=symbols['s3ce_hud_status_width_gateway'][0]
    before=bytes(v.mem_read(c,EXTENT))
    assert p.call(patch,(c,0x200000,c,EXTENT,gateway),absolute=True)==1
    after=bytes(v.mem_read(c,EXTENT))
    changed=[i for i,(a,b)in enumerate(zip(before,after))if a!=b]
    assert all(any(t<=i<t+4 for t in (0x1073cc,0x107500,0x1075e0,0x1077e0,0x107844,0x107848,0x10784c,0x107288))for i in changed)
    assert p.call(patch,(c,0x200000,c,EXTENT,gateway),absolute=True)==2
    corrected={k:tap(point)for k,(point,_)in targets.items()}
    for k,(_,expected)in targets.items():assert corrected[k][0]==expected,(width,height,scale,k,targets[k],original[k],corrected[k])
    if scale==1:assert original==corrected
    if scale==3.375:
        assert original['buy'][0]==[('pause',0)]
        assert original['wishes'][0]==[]
        assert original['mood_inner'][0]==[]
        assert original['mood_edge'][0]==[]
    render_tail=symbols['render_camera_tail'][0]
    def render(expanded):
        v.mem_write(scene+0x26a,bytes((int(expanded),)));draws.clear()
        p.call(render_tail,(scene,renderer,c+0x112f4c),absolute=True)
        expected=(0x12223344 if expanded else 0x56667788,
                  p.read(scene+0x25c),p.read(scene+0x260),18)
        assert draws==[expected]
        assert p.read(scene+0x264)==int(35*scale)
        return expected
    camera_checks=[]
    # Replay exactly the0.1.12 seven-word HUD generation: all new corrections
    # stay applied except the one newly changed camera word. This is disposable
    # instruction evidence, never a runtime phase/save mutation.
    camera_word=bytes(v.mem_read(c+0x107288,4))
    for expanded in (False,True):
        rendered=render(expanded)
        center=raw((rendered[1],rendered[2]))
        for camera_enabled in (False,True):
            v.mem_write(c+0x107288,source[0xd2a0+0x107288:0xd2a0+0x10728c])
            v.ctl_remove_cache(c+0x107288,c+0x10728c)
            old12={k:tap(targets[k][0],camera_enabled,expanded,dispatcher=True)
                   for k in ('plumbob','wishes','status','buy','pause')}
            if scale==3.375 and camera_enabled:
                assert old12['plumbob'][0]==[('camera',1-int(expanded))],(width,height,high,expanded,camera_enabled,old12)
                assert old12['wishes'][0]==[('camera',1-int(expanded))]
            v.mem_write(c+0x107288,camera_word)
            v.ctl_remove_cache(c+0x107288,c+0x10728c)
            fixed={k:tap(targets[k][0],camera_enabled,expanded,dispatcher=True)
                   for k in ('plumbob','wishes','status','buy','pause')}
            for k,result in fixed.items():assert result[0]==targets[k][1],(k,result,old12[k])
            if scale==1:assert old12==fixed
            camera_checks.append(dict(expanded=expanded,enabled=camera_enabled,
              render=rendered,old12=old12,corrected=fixed))
        for phase in (6,21,7):
            assert tap(center,True,expanded,phase=phase)[0]==[('camera',1-int(expanded))]
            assert tap(center,False,expanded,force=1,phase=phase)[0]==[('camera',1-int(expanded))]
        # Same logical35circle normalclick; same26circle for75% fallback.
        for distance,force,expected in ((33,0,True),(37,0,False),(24,1,True),(28,1,False)):
            point=raw((rendered[1]-distance,rendered[2]))
            result=tap(point,True,expanded,force=force)
            assert any(r[0]=='camera'for r in result[0])==expected,(width,height,scale,expanded,distance,force,point,rendered,result)
        # Actual dispatcher reaches force1 with enableflagoff; nearby world gap
        # proceeds after both passes instead of toggling the camera.
        result=tap(center,False,expanded,dispatcher=True)
        assert force_passes==[0,1] and result[0]==[('camera',1-int(expanded))]
        far=raw((rendered[1]-40,rendered[2]))
        result=tap(far,False,expanded,dispatcher=True)
        assert force_passes==[0,1] and result[0]==[('world',0)]
    return dict(high=high,width=width,height=height,scale=scale,
      cameraChecks=camera_checks,cameraExpandedStates=True,actualTwoPassDispatcher=True,
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
    summary=dict(cases=len(results),dispatchChecks=len(results)*9,cameraHudComparisons=len(results)*40,cameraBoundaryChecks=len(results)*24,passAll=True,results=results)
    if a.output:a.output.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items()if k!='results'},indent=2))
if __name__=='__main__':main()
