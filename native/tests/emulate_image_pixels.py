"""Execute original Image2D loading and compare compiled compatibility hooks.

The caller supplies the SHA-pinned original game and APK; no game assets or
private device report are bundled. Original image initialization, pixel setter,
mipmap generation and memcpy execute. Allocator results and error-cleanup
endpoints are modeled explicitly. This is ARM instruction evidence, not Android
execution or completed social gameplay.
"""
from pathlib import Path
import struct,hashlib,json,lzma,zlib,zipfile,time,argparse,subprocess,tempfile,os
from unicorn import *
from unicorn.arm_const import *
from emulate_context_menu import Machine, PROBE, SOURCE_SHA, EXTENT, OFFSET, SAVED
from emulate_stack_bridge import load_elf, symbol_table
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--source',type=Path,required=True)
ap.add_argument('--source-apk',type=Path,required=True)
ap.add_argument('--ndk',type=Path,default=os.environ.get('ANDROID_NDK_HOME'))
ap.add_argument('--output',type=Path)
args=ap.parse_args()
source=args.source.read_bytes();assert hashlib.sha256(source).hexdigest()==SOURCE_SHA
code=source[OFFSET:OFFSET+EXTENT];BASE=0xc3014000
OBJ=0xc13b74d0;HEAP=0xc4000000;BODY=0xc2ca3218;STAGING=0xc5000000;SP=0xf64ce9a8;STOP=0xf64dff00

def run(raw,source):
 fmt,mutable,width,height=struct.unpack_from('<BBII',raw,12)
 assert not mutable
 palette=struct.unpack_from('<I',raw,22)[0];assert palette==0
 count=struct.unpack_from('<I',raw,26)[0];pixels=raw[30:];assert len(pixels)==count
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for addr,size in [(BASE,0x200000),(0xc13b7000,0x1000),(0xc2c00000,0x200000),(0xf64c0000,0x20000),(HEAP,0x200000),(STAGING,0x200000)]:u.mem_map(addr,size)
 u.mem_write(BASE,code);u.mem_write(BODY,raw);u.mem_write(STAGING,pixels)
 for begin,count in [(0xa83a0,7),(0xa83d0,6),(0x126388,6)]:
  for off in range(begin,begin+4*count,4):
   target=struct.unpack_from('<I',code,off)[0]-0x4a000000
   assert 0<=target<len(code)
   u.mem_write(BASE+off,struct.pack('<I',BASE+target))
 cursor=HEAP;allocs=[]
 def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def alloc(_,pc,size,arg):
  nonlocal cursor
  n=u.reg_read(UC_ARM_REG_R0);address=cursor;cursor+=(n+15)&~15
  assert cursor<=HEAP+0x200000
  u.mem_write(address,b'\xa5'*n);allocs.append((n,address));u.reg_write(UC_ARM_REG_R0,address);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,alloc,begin=BASE+0x132ca4,end=BASE+0x132ca4)
 u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP)
 for register,value in [(UC_ARM_REG_R0,OBJ),(UC_ARM_REG_R1,fmt),(UC_ARM_REG_R2,width),(UC_ARM_REG_R3,height)]:u.reg_write(register,value)
 u.emu_start(BASE+0xa8354,STOP,count=100000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,source);u.reg_write(UC_ARM_REG_LR,STOP)
 u.emu_start(BASE+0xa84a0,STOP,count=200000000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 assert bytes(u.mem_read(source,len(pixels)))==pixels
 assert u.reg_read(UC_ARM_REG_SP)==SP
 object_words=struct.unpack('<19I',u.mem_read(OBJ,76))
 assert not any(BODY<=x<BODY+len(raw) or STAGING<=x<STAGING+len(pixels) for x in object_words)
 return [(n,hashlib.sha256(bytes(u.mem_read(a,n))).hexdigest()) for n,a in allocs]

def objects():
 a=zipfile.ZipFile(args.source_apk).read('assets/res.dz.jpg');n,d=struct.unpack_from('<HH',a,4);o=8;names=[]
 for _ in range(n+d):e=a.index(0,o);names.append(a[o:e].decode());o=e+1
 o+=n*6+4
 for i in range(n):
  off,size,dup,flags=struct.unpack_from('<4I',a,o+16*i);end=struct.unpack_from('<I',a,o+16*(i+1))[0] if i+1<n else len(a)
  if not names[i+1].endswith('.m3g'):continue
  data=lzma.decompress(a[off:end],format=lzma.FORMAT_ALONE) if flags&0x200 else a[off:end]
  assert data[:12]==b'\xabJSR184\xbb\r\n\x1a\n';pos=12;obj=0
  while pos<len(data):
   c,tl,ul=struct.unpack_from('<BII',data,pos);body=data[pos+9:pos+tl-4];body=zlib.decompress(body) if c else body;q=0
   while q<len(body):
    k,size=struct.unpack_from('<BI',body,q);raw=body[q+5:q+5+size];obj+=1
    if k==10:yield i,names[i+1],obj,raw
    q+=5+size
   pos+=tl

def compile_probe(ndk, directory, text):
 native=Path(__file__).resolve().parents[1]
 support=directory/'support.c';support.write_text(PROBE)
 output=directory/f'image-{text:x}.elf'
 cc=ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi26-clang'
 subprocess.run([str(cc),'-std=gnu11','-O2','-mthumb','-fPIC','-Wall','-Wextra','-Werror',
  '-fvisibility=hidden','-fstack-protector-strong','-nostdlib','-static',
  f'-Wl,-Ttext={text:#x},-e,s3ce_patch_image_pixels,--no-undefined',
  str(native/'image_pixels.c'),str(support),'-o',str(output)],check=True)
 return output.read_bytes()

def original_failure(raw):
 """The reported null staging allocation, with the original stream and memcpy."""
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 stream=0xc1499430;body=0xc2ca3218;frame=0xf64ce9a8
 for addr,size in [(BASE,0x200000),(0xc1499000,0x1000),(0xc2c00000,0x200000),(0xf64c0000,0x20000)]:u.mem_map(addr,size)
 u.mem_write(BASE,code);u.mem_write(body,raw)
 def w(addr,*values):u.mem_write(addr,struct.pack('<'+'I'*len(values),*values))
 w(stream,BASE+0x1614b0);w(stream+8,body);w(stream+0x10,0,len(raw),0,30)
 w(BASE+0x1614b0+0x30,BASE+0xb3108);w(frame+0x94,stream)
 u.reg_write(UC_ARM_REG_SP,frame)
 for r,v in [(UC_ARM_REG_R7,0xf64cea98),(UC_ARM_REG_R8,0xf64ceab0),(UC_ARM_REG_R9,0xc317605c),(UC_ARM_REG_R10,0xc13b74d0)]:u.reg_write(r,v)
 requested=[]
 def boundary(_,pc,size,arg):
  if pc==BASE+0xb1a44:u.reg_write(UC_ARM_REG_R0,0x1000)
  else:requested.append(u.reg_read(UC_ARM_REG_R0));u.reg_write(UC_ARM_REG_R0,0)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 for off in (0xb1a44,0x132ca4):u.hook_add(UC_HOOK_CODE,boundary,begin=BASE+off,end=BASE+off)
 try:u.emu_start(BASE+0x9c460,BASE+0x9c49c,count=100000)
 except UcError as error:assert error.errno==UC_ERR_WRITE_UNMAPPED
 else:raise AssertionError('original failed allocation did not reproduce')
 expected=[0,0xc2ca3238,0xffff8,0,stream,0x100000,0xf64cea34,0xf64cea98,0xf64ceab0,0xc317605c,0xc13b74d0,0,0]
 assert [u.reg_read(UC_ARM_REG_R0+i) for i in range(13)]==expected
 assert u.reg_read(UC_ARM_REG_PC)==BASE+0xd40
 assert u.reg_read(UC_ARM_REG_LR)==BASE+0xb3144
 assert u.reg_read(UC_ARM_REG_SP)==0xf64ce988 and requested==[1048576]
 return {'pc':'game+0xd40','lr':'game+0xb3144','all_report_registers_match':True,'failed_staging_bytes':1048576}

def compiled_case(raw, probe, high, malformed=False, palette_detached=False):
 p=Machine(source,high);v=p.vm;c=p.code
 load_elf(v,probe,0,set());symbols=symbol_table(probe)
 patch=symbols['s3ce_patch_image_pixels'][0]
 gateways=[symbols['s3ce_image_pixels_'+name+'_gateway'][0] for name in ('borrow','release')]
 before=bytes(v.mem_read(c,EXTENT))
 assert p.call(patch,(c,p.code_length,c,EXTENT,*gateways,0),absolute=True)==1
 after=bytes(v.mem_read(c,EXTENT));sites=(0x9c480,0x9c484,0x9c488,0x9c48c,0x9c490,0x9c494,0x9c498,0x9c4d4,0x9c4d8)
 assert all(any(site<=i<site+4 for site in sites) for i,(a,b) in enumerate(zip(before,after)) if a!=b)
 assert p.call(patch,(c,p.code_length,c,EXTENT,*gateways,0),absolute=True)==2
 image=p.zero(76);fmt,mutable,width,height=struct.unpack_from('<BBII',raw,12)
 p.call(0xa8354,(image,fmt,width,height))
 body=p.zero(len(raw));v.mem_write(body,raw);stream=p.zero(32)
 p.write(stream,c+0x1614b0);p.write(stream+8,body,len(raw),0,len(raw),0,26)
 frame=p.stack_top-0x200;p.write(frame+0x94,stream);p.write(frame+0x9c,body)
 p.write(frame+0x84,0)
 length=struct.unpack_from('<I',raw,26)[0]
 if malformed:p.write(stream+0x14,29)
 original_registers={r:0x12340000+i*0x123 for i,r in enumerate(SAVED)}
 for reg,value in original_registers.items():v.reg_write(reg,value)
 v.reg_write(UC_ARM_REG_R9,c+0x16205c);v.reg_write(UC_ARM_REG_R10,image)
 v.reg_write(UC_ARM_REG_SP,frame)
 cleanup=[]
 if malformed:
  # Observe the exact original cleanup endpoints selected by the adapter;
  # their implementation is not part of this malformed-body ownership proof.
  detached=p.zero(16) if palette_detached else 0
  def clean(off,values,sp):
   cleanup.append((off,values[0]));p.ret(detached if off==0xaf264 else None)
  for off in (0xa9548,0xaf264,0x135910,0xb73bc,0x132c94,0xb210c):p.hook(off,clean)
  saved=[original_registers[r] for r in SAVED]+[p.stop]
  p.write(frame+0xa4,*saved)
  endpoint=p.stop
 else:
  def stop(_,pc,size,arg):v.emu_stop()
  v.hook_add(UC_HOOK_CODE,stop,begin=c+0x9c4dc,end=c+0x9c4dc)
  endpoint=c+0x9c4dc
 v.emu_start(c+0x9c460,endpoint,count=200000000)
 assert v.reg_read(UC_ARM_REG_PC)==endpoint
 if malformed:
  order=[0xa9548,0xaf264]+([0x135910] if detached else [])+[0xb73bc,0x132c94,0xb210c]
  assert [off for off,_ in cleanup]==order,cleanup
  assert cleanup[0][1]==image and cleanup[-2][1]==body and cleanup[-1][1]==frame+0x8c
  assert v.reg_read(UC_ARM_REG_R0)==0 and v.reg_read(UC_ARM_REG_SP)==frame+0xc8
  assert all(v.reg_read(reg)==value for reg,value in original_registers.items())
 else:
  assert v.reg_read(UC_ARM_REG_SP)==frame and v.reg_read(UC_ARM_REG_R4)==body+30
  assert p.read(stream+0x1c)==len(raw)
  assert v.reg_read(UC_ARM_REG_R9)==c+0x16205c and v.reg_read(UC_ARM_REG_R10)==image
  assert body in p.active_allocations
  assert bytes(v.mem_read(body,len(raw)))==raw
  # Non-borrowed pointer still takes the original array delete at this site.
  fallback=p.zero(16)
  assert fallback in p.active_allocations
  p.call(symbols['s3ce_image_pixels_release'][0],(frame,c,fallback,length),absolute=True)
  assert fallback not in p.active_allocations and body in p.active_allocations
 return {'high_game_and_split_data':high,'malformed':malformed,'palette_detached':palette_detached,
  'production_patch_and_gateways':True,'error_cleanup_endpoints':len(cleanup),
  'borrowed_body_preserved':not malformed,'stack_and_saved_registers_checked':True}

start=time.monotonic();rows=[];kiss=None
for index,name,obj,raw in objects():
 baseline=run(raw,STAGING);borrowed=run(raw,BODY+30);assert baseline==borrowed,(name,obj)
 rows.append({'entry':index,'name':name,'object':obj,'mip_count':len(baseline)-1,
  'pixel_bytes':len(raw)-30,'alloc_bytes':sum(n for n,_ in baseline),
  'mip_digest':hashlib.sha256(json.dumps(baseline).encode()).hexdigest()})
 if index==641:kiss=raw
assert kiss is not None and len(rows)==107
failure=original_failure(kiss);cases=[]
assert args.ndk,'--ndk required for compiled production checks'
with tempfile.TemporaryDirectory(prefix='s3ce-image-') as directory:
 for text in (0x21000000,0xdb000000):
  probe=compile_probe(args.ndk,Path(directory),text)
  for high in (False,True):
   cases.append(compiled_case(kiss,probe,high))
   for palette in (False,True):cases.append(compiled_case(kiss,probe,high,True,palette))
summary={'image_count':len(rows),'all_mip_bytes_identical':True,'source_unchanged':True,
 'source_not_retained_in_object':True,'original_failure':failure,'compiled_cases':cases,
 'elapsed_seconds':round(time.monotonic()-start,2),'images':rows,
 'boundary':'Original allocator results and malformed cleanup endpoints are modeled; no Android gameplay is emulated.'}
if args.output:args.output.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({key:value for key,value in summary.items() if key not in ('images','compiled_cases')},indent=2))
