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
