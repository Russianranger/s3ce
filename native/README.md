# ARM32 Airplay compatibility layer

`legacy_loader.c` is a compatibility loader for the exact `libairplay.so` in the
supplied The Sims 3 APK. It is not an ARM64 port or an emulator.

The source runtime has ARM EABI4 instructions, 4,115 relative text relocations,
two absolute relocations, 130 PLT relocations, and an executable-stack request.
Its proprietary S3E game image is a separate LZMA-compressed asset. Bumping the
original APK's target SDK alone cannot fix these native compatibility issues.

## Build and verify

Use Android NDK r28c on Linux x86_64:

```sh
export ANDROID_NDK_HOME=/path/to/android-ndk-r28c
native/build.sh /path/to/libairplay.so
python3 native/verify_legacy.py /path/to/source.apk \
  --shim /path/to/libairplay.so --ndk "$ANDROID_NDK_HOME"
```

The new library goes in `lib/armeabi-v7a/libairplay.so`. Package the original
runtime unchanged as `assets/compat/libairplay-legacy.so`. The build must verify
source APK SHA-256
`d42d0bf4a663abc3b1bb2abd0b350d93b6a2fa687a3b902f111a40c38a94f0d0`.
Original runtime SHA-256:
`d93bc59497d377a9524aa8b3fa090aec0e32048bec4bb5e50b757c2f7234befe`.

Java startup calls `System.loadLibrary("airplay")`, then the static native method
`com.ideaworks3d.thesims3.GameBootActivity.nativeBootstrap(AssetManager, String)`
with the application's assets and files directory. Before bootstrap,
`nativeConfigureGraphics(boolean enabled)` selects PVRTC compatibility or the
original renderer. It returns false if changing modes after the legacy runtime
is loaded; restart the game process before changing modes. Disabling compatibility
bypasses PVRTC and diagnostics hooks and uses the original symbol-resolution
path. The mandatory pre-context string guard below remains active in both modes.

A positive bootstrap return is the
original JNI version; a negative return is failure. Bootstrap must finish before
starting the original game Activity. The original Activity's later library load
then reuses the already loaded shim.

## Typed Java GL startup before capability queries (0.1.5)

The Thor's first native tombstone identified `libGLESv1_CM.so glGetString+0x1c`,
called from the original runtime at offset `0x33987` before an EGL context was
current. Returning NULL in 0.1.3 exposed another assumption: the game passes its
extension string to `strlen` at S3E code offset `0x1134` without a NULL check.
In 0.1.4 the legacy window-start callback returned with no current context and no
pending exception, but no Java `glInit` entry was logged.

The old callback is no longer trusted as the initial Java dispatch. Actual Thumb
execution under Unicorn confirms that its cached method mapping and JNI call
branch are correct. It also confirms that the legacy `callMethod` helper invokes
`ExceptionDescribe` and `ExceptionClear` on a Java failure, then returns normally.
A zero pending-exception status after that helper is therefore insufficient to
establish that Java initialization ran successfully. The exact device-side Java
failure remains unconfirmed until the next report.

The mandatory string guard now invokes a typed starter on the engine thread:

1. Retain a local reference to the current AirplayThread receiver. The original
   `setViewNative` may delete and replace its global reference during GL-view creation.
2. Resolve the receiver class and private `glInit(I)V` method afresh for cache
   comparison. Resolve public `compatGlInit(I)V` afresh for invocation.
3. Invoke that bridge with `CallVoidMethodA` and an explicit integer argument.
   The Java bridge records entry, calls the unchanged private initializer, and
   records either completion or the full thrown stack before rethrowing it.
4. Require an actual current EGL context and no pending Java exception. Compare
   the retained receiver with the new global receiver, then refresh the original
   private-method cache using the fresh method ID.
5. Run the original native callback afterward for its existing GL tracking and
   version bookkeeping. The Java initializer now sees its existing GL view and
   skips duplicate window work.

This preserves Airplay's engine-mutex release, UI GL-view creation, surface wait,
mutex reacquisition, and same-engine-thread `eglMakeCurrent` sequence. It creates
no temporary pbuffer or UI-thread context and invents no capability strings.
Textures created after capability detection belong to the real window context.

Lookup and pre-entry exceptions are also persisted through the application-owned
`GameDiagnostics.recordGlFailure(Throwable)` helper, whose class and static method
are cached during UI bootstrap. A pending Throwable is temporarily cleared only
to record it; any logging failure is discarded and the **same original Throwable**
is restored before returning. Context initialization failure stops with a durable
EGL/JNI diagnostic and abort message instead of continuing into the known NULL
string dereference. A thread-local guard prevents recursive initialization.

The original string wrapper entry is `0x3397c`; its real dispatch slot is
`0x55a64`, derived from its Thumb LDR and checked against the ELF symbol. The
original window-start callback is Thumb entry `0x210a5`, verified against its
symbol, instruction fingerprint, and executable segment. Private Android state
`g_s3eAndroidGlobals` at `0x53af0` is validated against its original literal and
ELF symbol. Current JNI identity must match the environment saved by `runNative`.

`GLForceDLLVersion=0x0101` pins the legacy engine's detected version and avoids
recursive probing during startup; it does not itself choose a graphics driver.
The application still uses its existing GLES 1.1 library/context route. The
original intentional `GL_OES_framebuffer_object` extension filter is preserved.

## Graphics compatibility (0.1.1)

The original game stores 135 textures as PVRTC1, including its title background,
eyes, hair, and Create-a-Sim room. The first Thor run rendered ordinary textures
but omitted these compressed textures. All 135 images and their 691 mip levels
were decoded successfully on the host using the official PowerVR reference
implementation. No game artwork is included in this source repository.

The game's ARM capability initialization at `0x4a057764` queries
`glGetString(GL_EXTENSIONS)` and token-matches
`GL_IMG_texture_compression_pvrtc`. The GL lookup adapter therefore advertises
that extension when native support is absent and the software upload path is
available. On those GPUs, PVRTC1 RGB/RGBA 2/4-bpp uploads are decoded to RGBA8888
and uploaded with normal GLES texture calls, including full-image compressed
subimage reloads at offset zero. RGB formats get opaque alpha;
RGBA formats preserve their decoded alpha. GPUs advertising native PVRTC keep
their original compressed upload path.

Decoding is limited to power-of-two dimensions, at most 4096 per side and 16 MiB
of decoded pixels per upload. Minimum compressed block sizes and small mip levels
are validated before decoding. The temporary pixel buffer is released after the
synchronous upload. Nonzero-offset compressed subimages retain the original
driver path; the PVRTC1 extension permits full-image replacement only. This
adapter follows the original game's single-context rendering architecture. The MIT-licensed reference decoder and pinned upstream source
are documented in [pvrtc/NOTICE.md](pvrtc/NOTICE.md). Its license must also be
packaged with the APK.

The adapter logs the native renderer, version, extension list, initial texture
formats, and bounded GL errors. Errors inspected for logging are queued for the
game's next `glGetError` call. Runtime and S3E mapping addresses are recorded for
crash correlation. Bounded, durable before/after markers around initial string
queries, CPU decoding, and GPU uploads help identify the last operation before a
native crash; no signal handler or signal-time logging is installed. The decoder uses a static C++ runtime; no `libc++_shared.so`
installation is needed.

Run the CPU tests, optionally with sanitizers:

```sh
native/test.sh
S3CE_SANITIZERS=1 native/test.sh
```

These verify decoder colors, 2/4-bpp, alpha, small mip levels, invalid input and
output guards, conditional GL fallback, native-driver pass-through, context-start
ordering and recursion, typed JNI arguments, stale-cache bypass, and preservation
of the same Throwable even if the diagnostic helper fails. Set ANDROID_NDK_HOME
for the typed JNI test; it uses a temporary copy of the NDK's real JNI header.

The optional original-Thumb proof requires Unicorn 2.1.4:

```sh
python3 -m pip install -r native/tests/requirements-emulation.txt
python3 native/tests/emulate_gl_start.py /path/to/source.apk
```

It executes original `setViewNative`, `s3eGL_start`, and `callMethod` instructions
with mocked JNI/debug boundaries. Both GLES-version argument routes and injected
Java-exception clearing are checked. No emulator or vendor tool is bundled.

## Behavior

- Reads the trusted, packaged original runtime using Android's asset API.
- Maps its ELF segments privately, applies all supported ARM relocations before
  execution, then makes original code read/execute and original data read/write.
  Unused gaps become inaccessible.
- Resolves public Android libraries and embeds 22 ARM compiler-rt helper
  implementations. Supplies the obsolete `atexit` and `__srget` imports locally.
- Changes only the dedicated `s3eMallocOSCode` and `s3eFreeOSCode` entry points,
  guarded by exact original instruction bytes, to use private executable mappings.
  Ordinary game, audio, and asset allocations remain ordinary allocations.
- Retains the supplied runtime's instruction-cache flush routine. This routine
  also issues `mprotect(PROT_READ|PROT_WRITE|PROT_EXEC)` for loaded game code.
- Preserves the original JNI class names and RegisterNatives tables. Checks for
  JNI exceptions because the original JNI_OnLoad can return success despite
  registration failure.
- Logs startup, import failures, load phase, and executable-allocation failures
  to Logcat (`S3CECompat`) and `files/compat-native.log`.
- The shim itself has no text relocations, executable stack, or writable/executable
  ELF load segments, and is built with stack protection, RELRO, and immediate
  symbol binding.

## Scope and remaining device validation

This candidate requires a device with 32-bit ARM application support and 4 KiB
pages. Android version by itself does not establish those capabilities. ARM64-only
devices and 16 KiB page configurations require a different runtime implementation.

The S3E image contains mutable data alongside executable ARM code, so its dedicated
code mapping remains writable/executable. The application deliberately targets API
28 for this legacy runtime. Changing the target beyond that requires further
runtime work and device validation; changing only the manifest is not sufficient.
It is intended for direct installation, not Play Store submission.

The host verifier checks the exact source, simulates all 4,247 relocations,
verifies both allocator guards, audits all 131 used imports against API28 ARM NDK
system-library stubs plus the linked shim helpers, and checks the shim's ELF
protections. The original 0.1.0 loader has reached game menus and Create-a-Sim on the Thor.
The 0.1.1 and 0.1.2 candidates regressed startup on the Thor; 0.1.3 exposed the
subsequent NULL-string assumption, and 0.1.4 showed that the old JNI bridge had
not established a context. The 0.1.5 typed bridge and durable exception reporting
pass host checks. Android window startup and PVRTC rendering still require
hardware confirmation. Validation must cover loading, graphics, audio, input, save/reload,
suspend/resume, and relaunch after process death.
