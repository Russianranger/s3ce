# Analysis provenance and scope

Source APK: `The+Sims+3_signed.apk`, supplied in this task.
SHA-256: `d42d0bf4a663abc3b1bb2abd0b350d93b6a2fa687a3b902f111a40c38a94f0d0`.

REA: `Russianranger/rea` commit
`0365454a573eb52c7089320fd74bfd4a673b78ae` (6.4.0 source).
Audited JADX headless MCP 0.7.1 SHA-256:
`6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75`.

REA's normal CLI refused to start its Android engine because its process-ownership
check encountered a nested PID/proc mismatch in this environment. Its unmodified
Java metadata bridge was invoked directly as a shell child for manifest/class
inventory and focused method bodies. The same audited upstream engine supplied
complete class decompilations. REA's safety checks were not edited or disabled.
This was static analysis; no target application was run.

## Observed original structure

- Manifest: `com.ideaworks3d.thesims3`, target SDK 7, min SDK 3.
- One native library: `lib/armeabi/libairplay.so`, 410,811 bytes, ARM32 EABI.
- Legacy ELF has `DT_TEXTREL`, an executable-stack marker, and 4,247 relocations.
- `assets/The Sims 3.s3e.jpg` contains the LZMA-compressed proprietary ARM program.
- Original `Main` extends `AirplayActivity`; native registration covers
  `AirplayThread`, `AirplayView`, and `SoundPlayer`.
- Primary save root already used `getFilesDir`; optional card storage used the
  shared external root.
- `backlightOn`, phone-ID/number and optional contacts/location bridges use APIs
  unavailable without privileges or runtime permissions on current Android.

## Engineering limits

The shim is restricted to this input and exact allocator fingerprints. It is
not a general ELF loader or ARM emulator. No native source reconstruction or
64-bit translation is claimed. Dedicated S3E code allocations are still RWX;
newer target-SDK migration requires separating executable and writable parts of
the proprietary S3E image. The original lifecycle/audio/rendering code is largely
preserved and may contain additional problems only visible during gameplay.

Android's linker rejects legacy text relocations for target SDK >=23:
https://android.googlesource.com/platform/bionic/+/HEAD/android-changes-for-ndk-developers.md

Android 15's installable minimum target SDK is 24:
https://developer.android.com/about/versions/15/behavior-changes-all

16 KiB page behavior:
https://developer.android.com/guide/practices/page-sizes

## 0.1.1 graphics and input findings

The source data contains 135 PVRTC1 images (116 RGBA / 19 RGB), including the
title/room backdrops and hair/eye textures. All 691 stored mip levels decoded
with the pinned PowerVR reference decoder. The S3E capability initializer checks
GL_IMG_texture_compression_pvrtc before enabling this path. The shim implements
conditional software support rather than declaring unsupported GPU capability.
See native/pvrtc/NOTICE.md for the upstream source, license, and hashes.

The existing Game/SnapdragonAlphaWorkaround flag is read via s3eConfigGetInt at
unpacked S3E offset 0x14638c. It controls an existing dummy draw/texture-state
flush when enabling GL_ALPHA_TEST at offset 0xbce00. The Android-only config
addition enables that pre-existing behavior.

Original MultiTouch uses a pointer ID as a coordinate-array index and ignores
ACTION_CANCEL. The original DEX reproduces the sparse-ID failure. The original
resume handshake can lose an early notification during native/GL teardown;
the predicate-gated wait is covered by a latch-controlled host regression.

## 0.1.3 confirmed pre-context query

The device report shows the crash in platform glGetString at the original
wrapper's return offset 0x33987. s3eGLGetInt_platform 0x3f690 can call version
detection before Java EGL startup; its GL_VERSION call at 0x33acc therefore has
no current context. The existing GLForceDLLVersion configuration branch at
0x33a9c avoids this call. Section s3e is hardcoded by s3eConfigGet 0x2972c;
version 0x0101 is already used in the provided engine configuration.

The wrapper replacement also guards eglGetCurrentContext and delegates only
when current. Public EGL specifies EGL_NO_CONTEXT when none is current:
https://registry.khronos.org/EGL/specs/eglspec.1.4.pdf

The dispatch binding is g_glGetString 0x55a64, independently verified from the
original instruction/literal and ELF symbol. Full user reports stay private;
only technical crash offsets are recorded here.

## 0.1.4 real-context initialization

The next trace showed NULL strings from the guarded no-context query path,
followed by a fault at S3E code-relative 0x1134. The capability initializer at
unpackedfile 0x64a04 queries extensions at 0x64a14 and calls strlen at 0x64a30.
The original window initializer is s3eGL_start 0x210a5; it invokes the cached
AirplayThread.glInit method on the game thread. runNative acquires the engine
mutex before game execution, making the original Java unlock/UI/wait/relock
protocol valid at this lazy-init point. It is not valid before runNative.

The new binding and prerequisite checks use original symbols/instructions for
s3eGL_start and g_s3eAndroidGlobals. No OS-thread context is fabricated or moved
between UI/render threads, and early textures remain in the actual window's
context. Failed context creation is reported explicitly rather than returning
NULL into the known string dereference.

## 0.1.5 direct Java startup bridge

The 0.1.4 device report aborts because the original window-start callback returns
without a current context. No AirplayThread.glInit entry or EGL initialization
appears in its log; EGL reports success/no error and no JNI exception remains.
That last observation was insufficient: original callMethod at 0x20f14 invokes
ExceptionOccurred/ExceptionDescribe/ExceptionClear after the Java call.

Independent disassembly/NDK checks and Unicorn execution of the original
relocated Thumb bytes confirm setViewNative caches glInit(I)V at Android-state
+0x14 on the Thread receiver at +8. s3eGL_start passes version 1 or 2 through
CallVoidMethodV, JNI slot 62/offset0xf8. The wrapper thunk, Thumb state and
8-byte stack alignment are correct. These facts rule out several proposed static
ABI errors; they do not reproduce the device's missing Java entry.

0.1.5 bypasses that opaque startup dispatch. A fresh GetMethodID resolves a new
public compatGlInit(I)V wrapper; CallVoidMethodA passes an explicit jvalue.i=1.
The wrapper uses invoke-direct on the untouched original glInit and saves durable
entry/exit/failure markers and full exception stacks. The current game-thread
JNI environment and original lock/reference prerequisites remain required.
Only after the typed call has no exception and a real current context may the
original s3eGL_start run for its existing bookkeeping. A retained local Thread
reference must still identify the current global receiver before the freshly
resolved private method ID replaces its old cache entry. Java then skips duplicate
initialization because m_UseGL is true. No private version-state writes are
replicated in the compatibility layer.

The exact device-side cause in the original dispatcher remains unresolved.
This is a targeted route replacement with stronger diagnostics, not a verified
hardware startup result. Full reports remain private.

## 0.1.6 native fibre stack and ART entry

Device 0.1.5 resolved matching fresh/private method IDs, then CallVoidMethodA
left a Java exception without any compatGlInit entry. The already initialized
static Java exception logger also threw before its first body marker. Thus the
suspected method cache did not explain that run, and a Java logger cannot be
the sole diagnostic mechanism for pre-entry runtime rejection.

The source runtime always creates a fibre independently of StackSwitch:
s3eExecExecute0x18d5c reads StackSize, s3eExecStartGame0x1946c calls
s3eFibreCreate0x2e73c, and FibreSwitch_asm0x2e4a0 replaces SP at0x2e4b8.
FibreCreate allocates storage and initializes a new aligned SP. mymain0x194d0
stores the suspended original stack as g_LoaderStack0x56758 and enters the game.
The game entry preserves/aligns that SP, rather than replacing it itself.
Increasing StackSize cannot place a heap fibre inside ART's registered stack.

Android13 primary source ArtMethod::Invoke checks the native frame against
Thread::GetStackEnd before entering the Java method, throwing StackOverflowError
and returning if below it. The exact on-device Throwable type is not established
by the 0.1.5 report; foreign-SP rejection is supported by the binary path and
pre-entry failure pattern. References:
https://android.googlesource.com/platform/art/+/refs/tags/android-13.0.0_r1/runtime/art_method.cc
https://android.googlesource.com/platform/art/+/refs/tags/android-13.0.0_r1/runtime/reflection.cc

StackSwitchReadConfig0x3c944 defaults to0. The supplied global s3e.icf explicitly
disables it as a temporary development measure. External relocation branches
0x173e2/0x17572 select the existing native stack veneers when enabled.
0.1.6 adds Android StackSwitch=1 alongside the existing GL version override.
The lazy GL callback also uses the original generic thunk if its current stack
is outside the registered native thread bounds, preserving callback bookkeeping
and restoring the game stack afterward. EGL stays on the same thread.

A native-only exception classifier and stack-bound markers complement Java
logging. No ART private internals or hidden fields are modified. Hardware startup
is not established by the host ARM/stack regressions.

Enabled glGetString import slot133 has metadata0x34 and selects the original
Fast_Int32Ret3c78c stack thunk; glTexImage2D slot218 metadata0x20 selects generic
Void handling with eight stack words copied. Configuration files are loaded at
190ac before StackSwitchReadConfig1910a; global s3e.icf precedes app.icf, so the
app's Android override is present before external import veneers are generated.

Initial code extent0x166ad8 plus508*16+1024 enabled-veneer bytes reaches0x168e98,
inside the page-rounded0x169000 dedicated executable allocation. The original
rounded-core flush ends at0x167000. The guarded s3eExecICacheFlush169c9 replacement
expands known tracked allocation spans and forwards to original platform41021,
preserving mprotect7/cacheflush and return semantics. Unknown ranges keep their
original arguments. This covers initial and dynamic veneers without introducing
another executable allocator.

## 0.1.7 RAM preflight and gesture evidence

The new Thor screenshots/reports establish normal0.1.6 GL startup, room/hair PVRTC
uploads and Create-a-Sim rendering. Input counts increased while frames advanced
about60fps. Later frame stops align with logged focus loss/pause/GL teardown.
Fresh restart PIDs show the early insufficient-memory dialog before S3E code
allocation, which separates that symptom from the working rendering path.

get_mem_info(int&,int&) Thumb223b9 reads MemTotal/MemFree using signed32%d KiB
values, then LSL#10 at22416 converts into signed32 bytes. DeviceGetInt6 returns
free bytes;7 returns total. ExecDoInit190d8 compares the signed free result against
MemRequired(default0x80<<9=65536) and branches via1911a on low values, eventually
showing the reported zero-exec-size 'Not enough memory to begin loading s3e file'
text. There are other allocation-failure callers of that dialog, so the old
report alone does not establish the physical free-RAM value for the failing run.

Actual original Thumb execution reproduces false rejection at2/3/4/7/16GiB while
1/5GiB passes, and genuine32KiB fails. The guarded helper replacement reads64-bit
KiB, preserves MemFree semantics and saturates only unrepresentable signed-int
byte results. Zero/low remain low; unavailable fields remain-1. It logs raw KiB
and capped bytes. No SkipFreeRamCheck bypass or enlarged game allocation is used.

Actual original JNI/pointer ARM paths accept consistent4/5/6 events and publish
single button/motion callbacks for primary IDs0/7/31. The game registers single
callback events0/1; that synthesis exists. Primary matching, unchanged coordinates
and an optional movement timer are the native filters. No specific software
swipe defect was reproduced, so dispatch/queue/callback behavior is unchanged.

A guarded JNI registration row457d8 (function word457e0) wraps the exact original
onMotion handler once, preserving all6 JNI arguments and pending exceptions.
Bounded combined records show ID/type/coords and observational before/after
primary/pending/published state. Java records action/source/ID plus the actual
text-input gate and action totals.128KiB native report retention keeps initial
DOWN/RAM evidence alongside the compact trace. The next Thor report must locate
where delivery diverges before another behavior patch is justified.

## 0.1.8 callback delivery and game gesture boundary

The 0.1.7 Thor report and user result confirm reopening works. MemTotal is
15621188 KiB and MemFree 1441044 KiB in that run; the compatibility reader returns
INT32_MAX total bytes and 1475629056 free bytes. Startup continues normally.

Fourteen DOWN/UP pairs and 283 MOVE events reach JNI. The source is touchscreen,
ID is zero, the text-input gate is false, and large horizontal movement changes
native pending coordinates. The primary pointer remains selected until UP.
Frames continue during the attempts. Published polling coordinates stay zero,
but the game imports only PointerRegister, not PointerUpdate/GetX/GetY/GetState;
those unused polling fields are not evidence of lost callback motion.

Actual original ARM execution covers registration, JNI synthesis, event queue,
exact payload copying, DeviceYield dispatch, notification and callback stack
switching. Motion events can be dropped when event1 has no registered callback;
registration/delivery is the remaining missing device witness. The original game
registers event0 and event1, reads both callback coordinates without a gesture
filter, and queues them into two 50-entry AppEngine buffers. Frame consumption
flips and drains those buffers. A matching primary drag crosses the original
10-pixel threshold and reaches state3; state3 emits gesture event5 each tick.

The actual Create-a-Sim handler for menu state13 converts horizontal delta to
negative360 times delta/width, updates the Sim angle, inertia and timer, and the
renderer reads that angle. Original math helpers and high-address execution
pass. No hidden acknowledgement, hitbox, float ABI or extra timing gate was
established. These are host ARM execution results, not hardware gameplay.

The caller can still gate rotation when SceneMenu's UI selector at+0xf8 is
active, or AppEngine's transition flags at+0x420/+0x430 block routing. Selecting
a UI element also resets gesture state and pointer ownership. Transition value,
direction and speed are at+0x424/+0x428/+0x42c. The observer includes these fields;
their source semantics do not establish which gate, if any, is active on the
device.

The observer must preserve callback identity across duplicate registration and
unregister, use the generic stack gateway for its C proxy, and invoke the game
through the original callback gateway. Fast switching would bypass nested stack
bookkeeping. Code and initialized game data are separate allocations; preferred
global offsets must be resolved through guarded relocated literal pools rather
than added to the code base. Only validated objects may supply state snapshots.
Full reports and signing material remain private.

## 0.1.8 device follow-up: tutorial confirmation

The new report establishes the previously missing boundary. Original pointer
callbacks for events0/1 register successfully, every recorded native movement
enters the game's callback, AppEngine queue counts alternate and drain, and the
SceneMenu gesture state reaches3. Transition flags420=0/430=1 and route=-1 leave
input enabled. The Sim angle remains zero while menuState is12, not13.

The switch at114568 subtracts3 before indexing its table at114578. State12 maps
to114c9c; state13 maps to114cbc and then11b644 (the rotation handler already
executed in regression tests). State12 accepts logical event11 only when its
payload action intersects0x84, then requests13 through116944. Direct tap gesture3
and drag5 do not advance it. Independent actual ARM execution covers the phase
write and the original transition gate, including report-matching flags.

State12 entry116fec configures the instruction widget at Scene+168 with string
keys86c/86d for the first welcome hint, or84f/851 for edit appearance. The shipped
English archive confirms86d is the exact visible welcome/swipe instruction.
This prompt describes the next interaction but waits for a separate confirmation.
Its button requires DOWN/UP inside a35-unit circle, then a400ms release animation
before emitting action4. Pointer movement outside the circle cancels the click.

Source input mapping and inverse rendering both use3.375 at1920×1080. Actual ARM
execution reproduces the report coordinates; extra Java rescaling would break
this matching pair. Mesh96 has raw X coordinates±296 and positionScale0.5; the
bounds builder applies that scale, giving layout width296. The hint draw stores
the confirmation hit center at sceneX823 and sceneY=540-(bodyHeight+100)/2+23.
Inverse mapping puts X near498; three visible lines suggest Y near370. The35-unit
radius is about118 screen pixels, so a clean tap near500,370 is the practical
next hardware check. Exact wrapped body height is not recorded by0.1.8; this
point is source/screenshot-derived, not a hardware-confirmed center.

The reusable native/tests/emulate_cas_tutorial.py now executes that complete
button route at low/high code and separately allocated data addresses for
body heights45/60/90. Actual vertex-buffer scaling/bounds/width, layout, input
conversion, circular capture/release, animation, action emission and phase
dispatch all execute original ARM instructions. A clean raw500,370 tap stays
in12 through400ms and advances13 at401ms in all six cases. The two recorded
off-target taps do not. Generic temporary storage, sprite/audio output and
post-commit phase resource creation are modeled.

Sprite119 is a blue round background and glyph122 a black X in the shipped atlas;
the assets contain visible pixels. The supplied screenshot lacks these and the
dialog frame while font text and3D rendering remain visible. Asset absence and
native input loss are ruled out for this report; the missing2D sprite rendering
still needs investigation. No production input or rendering behavior was changed
for this follow-up. The existing0.1.8 APK can test dismissal before another build.

Bounded rendering review found that these sprites use normal M3G meshes with
alpha blending, depth testing/writing disabled and no culling. Their sampler
uses LINEAR magnification and LINEAR_MIPMAP_NEAREST minification. Whether the
specific live UI atlas receives or generates all required mip levels remains
unverified; the base-only upload logs do not prove incompleteness. Do not apply
a texture-filter workaround without establishing that remaining condition.

## 0.1.9 HUD draw-path compatibility candidate

The next Thor report confirms successful hint dismissal, state13 rotation with
changing angles, and state15 character/traits interaction. Missing UI artwork
persists. Visible blue hand buttons exactly match standalone btn_hand.png;
missing panels/icons use M3G HUD atlases. The control hit targets still work.

Asset inspection finds all HUD groups01–09 have intact RGBA8 Image2D data and
visible pixels, with no encoded no-mipmap flag. Source constructors/generators/
upload loops produce complete alpha-bearing mip chains. Original material setup
disables alpha/depth/culling as expected and uses source-alpha blending. Actual
SHORT position/UV array setup, color, transforms, implicit strip parsing and
GL draw parameters are valid in host execution. The orthographic camera is also
valid. No exact live Adreno failure is established by these checks.

All530 HUD sprite meshes share one implicit TriangleStripArray in anim2d.m3g:
encoding01, start0, one strip of length4. Visible room meshes use explicit index
arrays. The controlled candidate converts only that shared object to encoding81
with indices0,1,2,3 and the same strip length. Actual original ARM parsing and
rendering at low/high separately relocated addresses show the intended change
is DrawArrays(TRIANGLE_STRIP,0,4) → DrawElements(TRIANGLE_STRIP,4,UNSIGNED_SHORT,
[0,1,2,3]); all other captured calls, matrices, colors and buffers match.

Independent Mesa fixed-function comparisons cover all530 meshes.520 use exact
supplied texture assets and original ARM-generated mip levels.10 reference an
optional export texture absent from both supplied archives; those use labeled
geometry-control textures rather than claiming original-art validation. Both
index representations produce byte-identical pixels in every case. This proves
intended equivalence, not that the original API is generally broken or that the
Thor UI is repaired. The published candidate requires a device result.

patches/ui_indices.py pins the original archive and raw M3G hashes. It changes
only TSA object5 plus required header sizes, section lengths and Adler32 values.
Ordered LZMA stream replacement shrinks res.dz by35 bytes and adjusts subsequent
file offsets. All677 other compressed payloads and decoded entries remain
byte-identical. Nonmonotonic append/retarget was deliberately avoided because
legacy reader extent semantics were not established. Other game/audio/texture
assets are unchanged. Build and final-APK verification apply the same guard.

The GPU witness records the first8 matching quad-strip draws and powers of two
through2^20, at most25 snapshots. It logs active/server/client texture units,
binding/filter, array enables, caps, color/viewport and projection/modelview/
texture matrices through valid GLES1.1 queries. No state is written or client/
index memory dereferenced. Optional-symbol/no-context failures skip observation;
existing and query-generated GL errors are preserved through the prior queue.
The UI GPU label identifies a draw shape, not a confirmed atlas. This evidence
will locate live state differences if the equivalent indexed path still fails.

Release transport now reuses matching spans within changed large STORED members,
so editing a small archived resource does not upload the full26 MB member as a
literal. Bounded distinctive anchors and exact edge comparisons affect only
reconstruction transport. The final signed APK is reconstructed byte-for-byte
and hash-verified before publication; the existing manifest format is retained.

Reference checked for texture/completeness/query semantics: Khronos OpenGL ES
1.1.12 specification, sections3.7.7–3.7.9:
https://registry.khronos.org/OpenGL/specs/es/1.1/es_full_spec_1.1.pdf
