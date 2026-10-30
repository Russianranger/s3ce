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
