# Candidate 0.1.1 validation

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
