# Candidate 0.1.8 validation

The user confirms reopening works after 0.1.7. Its report shows large horizontal
swipes reach JNI with the text gate clear and frames continuing. Create-a-Sim
still does not respond. No swipe fix is established.

Completed:

- Eleven native ASan/UBSan suites pass, including callback identity/forwarding,
  every failed state-reader access, split code/data guards, map boundaries,
  worst-case output length and existing graphics/JNI/RAM regressions.
- Eighteen compiled production-proxy ARM scenarios pass, including proxy text
  at0xdb000000 and separately relocated high game/data/heap/stack addresses.
  Original registration, dynamic generic veneer, queue/copy/Yield/Notify,
  nested callback gateways, game adapters, frame drain and gesture states execute.
  Cookies, return values, R9, callee-saved registers, SP and fibre state survive.
  Duplicate/unregister/reentry, allocation failure and slot-limit pass-through
  retain original registry behavior.
- Original game drag threshold, gesture tick and full CAS rotation math pass at
  low/high addresses with real helpers. Only unrelated OS/UI effects are modeled.
  These are host instruction fixtures, not an Android VM or device gameplay.
- Independent review approves guarded register/unregister hooks, generic stack
  bookkeeping, stable callback identities, split-data literal resolution, class
  checks and readable-memory copies on the source-proven engine thread.
- ARM warnings-as-errors build,4247 relocations,131 legacy imports, native ELF
  hardening, original asset/configuration guards and APK signatures pass.
- All310 executable APK methods pass static DEX type/control-flow analysis against
  SDK35. Actual assembled touch-wrapper, pointer-ID/CANCEL, lifecycle lost-wake
  and GL-wrapper regressions pass. This does not establish ART/device execution.

Same certificate/application ID and data location; versionCode108, target28.
Callback tracing changes no intended input semantics. Bounded snapshots are
recorded after callback enqueue, before a later frame may consume that input.
The new hardware report must establish registration/delivery, queue drain and
Scene routing state. Reopening and room/hair rendering were already confirmed.

APK SHA-256:
`5889dd74a5094603e78534fcde915590ae1cb87d45c7f0252eb5fa4d51d0143a`.

Shim SHA-256:
`3b9397d65bafe7921185b48390183bbd006004bfd18dcf37dc50b4c990ac7912`.

Byte-exact reconstruction from the pinned0.1.0 base APK passed. Independent
publication/download verification pending.

## Historical 0.1.7 checks

Device0.1.6 evidence confirms startup/Create-a-Sim, working room/hair textures,
PVRTC uploads and continued frames during touch arrivals. Swipes remain blocked.
Restart shows a preallocation insufficient-memory dialog in fresh processes.
The reports contain old0.1.5 tombstones too; those are historical failures.

Completed:

- Exact original RAM-reader/DeviceGetInt6/preflight Thumb execution reproduces
  false low-memory rejection for multi-GiB values and genuine low-memory rejection.
- Guarded64-bit MemTotal/MemFree parsing and signed-int byte saturation preserve
  low/zero/unavailable values; host tests cover malformed/overflow input too.
  Raw/capped readings make the next physical restart result observable.
- Eight native ASan/UBSan suites, ARM compilation with warnings as errors,
  exact source guards,4247 relocations,131 import/hardening audit pass.
- Actual original JNI pointer routines publish expected single/multi movement for
  sparse IDs and preserve secondary-finger isolation. No swipe behavior defect
  was established by these host executions.
- Exact JNI registration row/name/signature/function fingerprint and writable
  globals span are checked before installing the observational wrapper. It calls
  the original once with unchanged arguments and leaves Java exception state.
- Java action/source/gate production counters, report retention and full-app
  compilation pass. Native trace and report memory remain bounded.
- Independent code/ABI review approved the RAM correction, forwarding and128KiB
  native-log retention. Working graphics/stack configuration is unchanged.

Final APK checks passed:310 executable methods with zero static DEX type/control-
flow errors against SDK35; actual assembled touch wrapper/gesture/lifecycle/GL
regressions, including the diagnostic descriptor, text gate and CANCEL release;
original asset/configuration preservation, APK signature/identity(versionCode107),
and byte-exact release reconstruction. This is host/static verification, not ART
or Thor gesture execution.

APK SHA-256:
`202e92142bbaca64ed769a06df21e7b5f6609470330432a4d34d1def670c85fb`.

Shim SHA-256:
`215636395d2e539db5f06e23815ccb38d6b4877660a941b4a76d1c8f9ec3897e`.

Publication run [41156929416](https://github.com/Russianranger/s3ce/actions/runs/41156929416)
passed reconstruction, signature/identity checks, prerelease upload and independent
download/SHA-256 verification. Published APK size/digest match the frozen local
artifact. Published source `9a6c82ef217a4a206c73592dc12b9df67adf93d4`.
RAM restart confirmation and the cause of the device swipe failure remain pending.

## Historical 0.1.6 checks


Device evidence: 0.1.5 resolved matching fresh/cached private method IDs, then
both its typed Java GL wrapper and static Java exception logger failed before
entering their method bodies. No Java GL file was created. The exact Throwable
type was unavailable in that report.

Binary/source findings:

- Game startup unconditionally creates and enters a heap fibre. StackSwitch=0
  disables native import/callback switching, rather than that initial fibre.
- Exact Android13 ART source checks native frame bounds before managed entry,
  throwing StackOverflowError and returning before the Java method starts.
  Foreign-stack rejection explains the observed pattern; the old report did not
  establish the actual on-device exception type or native SP.
- Original ARM trampoline execution moves the callback from a foreign SP onto
  the saved native thread stack and restores the game SP afterward. The supplied
  engine provides full callback/reentry bookkeeping for that route.
- Enabled veneers occupy reserved space in the dedicated executable allocation,
  not a non-executable malloc allocation. The original final flush covers the
  rounded core code extent; part of the larger enabled veneer area lies beyond
  it and requires explicit coverage before first execution.

Completed verification:

- Android-only StackSwitch=1 plus the existing GL version override passes exact
  original-byte, idempotence and mutation-rejection checks. All other original
  game assets stay unchanged and stored for file-descriptor playback.
- The compiled production ARM bridge plus original ARM/Thumb gateway passes eight
  emulated scenarios: raw foreign-stack rejection, native entry, nested callbacks,
  disabled-swap refusal, invalid saved pointers, guard/headroom boundaries, thread
  identity mismatch, and SP/register/fibre-state restoration. Callee-saved integer
  and d8-d15 registers survive caller-saved VFP clobbers. pthread/ART predicates
  are mocks; this is actual ARM instruction execution, not an Android VM.
- Six ASan/UBSan native suites pass, including all generated-veneer flush coverage,
  typed JNI, original Throwable preservation, partial diagnostic cache recovery
  and no-Java-method exception classification. ARM warnings-as-errors build passes.
- Full-allocation flushing retains original platform mprotect/cacheflush behavior
  and return values; unknown ranges retain their original arguments. Binding,
  Thumb fingerprints, globals and executable mappings are independently reviewed.
- All309 final APK methods pass static DEX type/control-flow analysis against
  SDK35. This is not ART execution. Original wrapper/lifecycle code is unchanged.
- All4247 relocations,131 legacy imports, native ELF hardening, asset/configuration,
  application identity, APK signatures and byte-exact release reconstruction pass.
  Same certificate/app ID; versionCode106.

APK SHA-256:
`3b7b82da9ed56a8c0c2cf9afb0abd4c653eb1a1c63ebb04f774d5b0f7d726cd8`.

Shim SHA-256:
`500525a6fe3a2f382f8445aa1ed13b91cbc2b7fc9ff5478ff537f5bcdfb75025`.

Publication run [41155065375](https://github.com/Russianranger/s3ce/actions/runs/41155065375)
passed reconstruction, signature/identity checks, prerelease upload and independent
download/SHA-256 verification. The release asset size/digest matches the frozen
local APK. Published source `1b9e216947939308327287bb76decbd035829938`.
Hardware startup/rendering/input/save results remain unverified.

## Historical 0.1.5 checks


Device evidence: 0.1.4 aborted after its original startup callback returned
without a current context. No Java glInit/EGL entry appears in the report.
The old JNI helper describes and clears exceptions internally, so the reported
post-call exception status did not prove a successful call.

Completed implementation:

- The original cache/receiver/descriptor/JNI table slots and ARM stack/Thumb
  state were independently checked. Actual relocated Thumb instruction execution
  verifies relevant setViewNative cache setup and version1/version2 JNI arguments.
- Fresh JNI lookup and CallVoidMethodA enter a new public compatGlInit(I)V wrapper.
  That wrapper invokes the exact, hash-guarded original private glInit directly;
  its mutex/UI/surface lifecycle is unchanged.
- Durable Java GL entry/exit/failure logs are included in exported reports.
  Native JNI errors remain pending for the guard instead of being swallowed.
- Only after the typed startup succeeds with a real current context may the old
  callback perform its existing version/window bookkeeping. No private state
  writes are duplicated in the shim.

Completed verification:

- Actual old Thumb dispatch tests cover both GL versions and injected Java
  exceptions, confirming the legacy describe/clear behavior.
- Four native sanitizer suites pass, including typed JNI calls with the NDK's
  real JNI header, stale cache IDs, exact int1/int2 arguments, and preservation of
  the same Throwable when the Java logger itself throws.
- Original glInit guard, additive-wrapper idempotence/tamper rejection, actual
  wrapper DEX success/failure with identical exception rethrow, touch/lifecycle
  regressions and real Java file-logging failure/persistence checks pass.
- The final APK has 309 executable DEX methods; static type/control-flow analysis
  against the Android35 framework reports zero errors. This is not ART execution.
- ARM compilation with warnings as errors, 4,247 relocation simulation, 131 import
  audit, ELF hardening, original asset/configuration guards, APK signatures and
  identity checks pass. App ID/certificate remain unchanged; versionCode105.
- Release reconstruction from the pinned 0.1.0 APK matches the signed APK exactly.

APK SHA-256:
`69d26e8f6d96d67b64c2366811e9ed796231d9919ac2076a6c3c87d9bdc543db`.

Shim SHA-256:
`27495c5d7a8619055bd2a214026383636db3f4c0c115ee54a921f681dd72b4cd`.

Publication run [41152986602](https://github.com/Russianranger/s3ce/actions/runs/41152986602)
passed reconstruction, signature/identity checks, prerelease upload, and independent
download/SHA-256 verification of the published APK. Release asset size/digest also
match the frozen local APK. Published source:
`c508de5dacb8ee0a0c41eecf0a29926d63bd7447`.
Hardware startup/rendering/input/save results remain unverified. The exact
cause of the device's original JNI-dispatch failure remains unresolved.

## Historical 0.1.4 checks


Captured 0.1.3 evidence: early GL string queries had no current context and were
blocked; the game then crashed at code-relative PC 0x1134 in its unchecked string
length path. This confirms the 0.1.3 NULL-return fix was incomplete.

Completed:

- Trace of the game capability initializer shows an extension query followed by
  unconditional strlen. A real context/string is required before that code.
- Lazy startup uses original s3eGL_start Thumb entry 0x210a5. Its instruction
  fingerprint, ELF symbol and executable mapping are verified.
- Private Android state 0x53af0 is cross-checked against its symbol and original
  literal 0x210f0. Saved game JNIEnv, thread reference+8, glInit methodID+14, and
  allocated engine-lock pointer+10c are checked before the callback. UI input
  callbacks do not overwrite the saved environment.
- Original runNative holds the engine lock before game execution. Reusing its
  original glInit path correctly releases it for UI surface creation and relocks
  afterward. No Java GL call is made prematurely or on the UI thread.
- Host sanitizer tests model first-query initialization, valid current-context
  dispatch, safe nested calls after creation, recursive/failed startup, required
  NULL results and a pending JNI exception despite successful context creation.
  These are host control-flow tests, not an Android EGL simulation.
- Independent reviewers approved callback/binding/thread/mutex semantics.
- Existing PVRTC regressions, ARM compilation,4,247 relocations,131 import audit,
  native hardening, guarded configuration/original asset checks, APK assembly and
  signatures pass. Same app ID/certificate, versionCode104.
- Publication run [41150906072](https://github.com/Russianranger/s3ce/actions/runs/41150906072)
  passed exact reconstruction, signature/identity verification, release upload,
  and independent download/SHA-256 verification of the published APK.

APK SHA-256:
`31dd1d1483e91325fcc79f313eb127439c7b4f391d723267d0fbf2e78c593aa3`.

Shim SHA-256:
`ddbf3fd394ae8d69975a22e675994300ec69d9238c5a52115b0b495d944bddce`.

Not yet established: actual Thor EGL window startup, menu/gameplay rendering,
input and save/reload. Failed initialization now has an explicit diagnostic,
but host checks do not establish that the device initializer will succeed.

## Historical 0.1.3 checks


Captured device evidence: both rendering modes crashed in platform
libGLESv1_CM glGetString, from original Airplay wrapper return offset 0x33987,
while startup logs had no GL view/context initialization. The engine's separate
s3eGLGetInt_platform path can query GL_VERSION before s3eGL_start.

Completed:

- Disassembly traces early GetInt at 0x3f690 to DetermineGLVersion 0x33a80,
  GL_VERSION call 0x33acc, wrapper 0x3397c and driver call 0x33986, matching the
  reported return PC. No new Java EGL initialization runs on the UI thread.
- Existing config escape GLForceDLLVersion is read at 0x33a9c from section s3e.
  0x0101 uses the provided runtime's GLES1.1 version encoding and skips the probe.
- Exact original app.icf digest, idempotency and tamper guards preserve all bytes
  except the Android-only override. Alpha workaround remains absent.
- The shared native replacement checks eglGetCurrentContext before driver calls,
  handles NULL safely, and preserves normal/current-context results plus the
  original FBO extension filter. It is applied in both rendering modes.
- Independent review corrected a dispatch-slot binding before release. The
  verifier derives literal 0x339e4/table 0x55a44/slot 0x55a64 from the original Thumb
  instruction, cross-checks the g_glGetString ELF symbol and writable segment,
  and verifies the exact8-byte wrapper entry fingerprint.
- Native host tests with sanitizers cover missing/current contexts, all GL string
  names, NULL driver returns and filtering. Existing PVRTC tests also pass.
- ARM compilation, 4,247 relocation simulation, 131 import audit, native segment
  protections, asset/config integrity, APK assembly and v2/v3 signatures pass.
- Same app ID/certificate; versionCode103. Saved data is preserved.
- Publication run [41149513664](https://github.com/Russianranger/s3ce/actions/runs/41149513664)
  passed reconstruction, signature/identity checks, release upload and independent
  download/SHA-256 verification of the published APK.

APK SHA-256:
`9dd9eef9c6135f2b449b9709c7eb41a087cddc9203c2cd69aad5859b362093f3`.

Shim SHA-256:
`720a2a2fb5dde8097524280b153a5051603e908f6851fe2e759403a978338487`.

The captured failure path is corrected in code. Reaching the menu, correct
texture display, swipe/tutorial progression, gameplay and persistence still
require Thor confirmation. Host/static checks do not establish those results.

## Historical 0.1.2 checks


Reported device result: 0.1.1 crashed during startup, and its text-only share
could not be saved by the file manager. No exact crash trace was supplied.
The startup crash cause remains unconfirmed.

Completed:

- Report export uses ACTION_CREATE_DOCUMENT with a nonempty .txt filename and
  writes/closes the selected URI on a worker before reporting success.
- Attachment sharing provides EXTRA_STREAM, ClipData, read grant and a
  read-only ContentProvider in the separate :launcher process. Canonical path
  and generated-name checks restrict access to report files.
- Java exceptions persist before Android's ordinary crash handler. Own-package
  ApplicationExitInfo history and bounded native tombstone summaries are added.
- Pure Java tombstone-parser tests pass all 33 cases, including malformed and
  unknown fields, bounds, trace ordering, and output limits.
- Independent review and DEX type/register/control-flow analysis of the final
  APK: 302 executable methods, zero analysis errors.
- ARM cross-compilation, all 4,247 relocations, 131 imports, native ELF hardening,
  identical original assets/configuration, APK assembly and signatures pass.
- The same application ID/certificate is retained; versionCode 102.
- GitHub publication run [41147877179](https://github.com/Russianranger/s3ce/actions/runs/41147877179)
  passed byte-exact reconstruction, APK signature/identity checks, publication,
  and independent download/SHA-256 verification of the published APK.
- Native rendering mode can bypass all new GL interposition. Durable log markers
  bracket initial GL queries, PVRTC decoding and GPU uploads. All 691 actual
  texture mip levels also passed host sanitizer checks; no native cause proven.

APK SHA-256:
`5c9820bfd8bd1682a9026c939f4ab1ca73828b4f839072f8d8a38ec92749e615`.

Shim SHA-256:
`002d713649bc2040da0a1ba09646c73d86b3f7a93c6466eda227f103c687ce0c`.

Not verified on hardware: saving through the document picker, reading through a
recipient file manager, retained exit records availability, and actual game
startup/rendering/input. Host and static checks do not establish those outcomes.

## Historical 0.1.1 checks


User evidence: 0.1.0 reached menus and Create-a-Sim on the Thor, with white
backgrounds, missing hair/eyes, and an unresponsive swipe tutorial. These are
not recorded as a gameplay pass.

Completed for 0.1.1:

- Located 135 PVRTC images and decoded all 691 stored mip levels on the host.
  Recovered room, title, eye, and hair textures were visually inspected.
- Verified the original capability gate checks the PVRTC extension; the adapter
  advertises software support only when the native driver lacks it.
- Native sanitizer tests cover all four PVRTC1 formats, tiny mip levels, buffer
  bounds, unaligned input, native-driver pass-through, full-image reloads, and
  GL-error preservation.
- Actual assembled DEX gesture regression covers complete swipes, sparse IDs,
  pointer removal, and cancellation. The original DEX reproduces the index/ID
  failure in the same host instruction-subset harness.
- Latch-controlled JVM regression reproduces the original lost resume wake and
  checks early/normal/spurious wake handling. Native callback blocking remains
  outside this host model.
- Exact input/method/configuration guards, APK assembly, Java compilation,
  original asset preservation except the guarded alpha configuration, embedded
  license, ARM native hardening/import/relocation audits, and APK signatures pass.
- Application ID and certificate match 0.1.0; versionCode is 101. Launcher runs
  in :launcher with a distinct task affinity; the engine runs in the main
  process. The report path makes no calls into the engine.
- Release reconstruction from the pinned 0.1.0 APK produces byte-identical 0.1.1.
- GitHub publication run [41146391540](https://github.com/Russianranger/s3ce/actions/runs/41146391540)
  passed reconstruction, APK signature/identity verification, prerelease upload,
  and a fresh download of the published APK with matching SHA-256.

APK SHA-256:
`c005793c54cc4220b173d9623032b927185531e41170644568216a0dfde2c42a`.

Shim SHA-256:
`8fce4aa2478654803504d8daee48c9e153c5a12cf6c2ab29460f2bab9b899d84`.

0.1.1 has not been run on an Android device here. Actual texture rendering,
Create-a-Sim progression, save/reload, audio, and process/task behavior need the
next Thor test. Android 14–16 runtime coverage is still unverified.

## Historical 0.1.0 checks


Completed in the build environment:

- REA/JADX static manifest, class and method inspection against exact input.
- Exact method-byte guards, idempotent patch application, and rejection of
  altered original method bytes.
- ARMv7/API26 shim cross-compilation with NDK r28c, `-Wall -Wextra -Werror`.
- Host simulation of all 4,247 original ELF relocations and allocator-site guards.
- Shim ELF inspection: no text relocations, no executable stack, no writable
  executable `PT_LOAD` segments. This describes ELF segments, not the S3E
  program's separately allocated executable memory.
- Original game assets and embedded legacy ELF unchanged; all original assets
  remain ZIP_STORED for file-descriptor playback.
- Launcher compilation against Android 35 and D8 assembly with min API26.
- Apktool reassembly, ZIP integrity/alignment, APK v2/v3 signatures.
- Final manifest/app ID/target/permissions checked with Android SDK `aapt`.
- GitHub publication run [41144292465](https://github.com/Russianranger/s3ce/actions/runs/41144292465)
  passed assembly, signature/identity checks, prerelease upload, and independent
  download of the published bytes for SHA-256 verification.

Published APK SHA-256:
`0605ca913169bc5f17ee2291c6ef20208322676f49e21489ceb8fb2f7ddb0381`.

Signing-certificate SHA-256:
`3c3d5fdfb1db4082e7e488773c2d59cd56ad77c4bfc0aa2e66076e988f02a0c4`.

Not completed:

- Installation/launch on a device or Android emulator.
- Reaching gameplay, saving/reloading, audio, lifecycle, or performance testing.
- Runtime verification on Android 13, 14, 15, or 16.

The release is an experimental compatibility candidate. Successful compilation,
relocation simulation, and signature checks do not establish a playable port.
