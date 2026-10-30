# Candidate 0.1.0 validation

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

Not completed:

- Installation/launch on a device or Android emulator.
- Reaching gameplay, saving/reloading, audio, lifecycle, or performance testing.
- Runtime verification on Android 13, 14, 15, or 16.

The release is an experimental compatibility candidate. Successful compilation,
relocation simulation, and signature checks do not establish a playable port.
