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
