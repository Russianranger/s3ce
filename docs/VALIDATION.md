# Candidate 0.1.3 validation

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
