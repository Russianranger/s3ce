# S3CE — The Sims 3 Android compatibility project

Experimental preservation build of the user-supplied Android game, using
[Russianranger/rea](https://github.com/Russianranger/rea) to inspect its original
Java/JNI bridge. **0.1.10 restores the missing UI and has completed a real Android
playthrough of female character creation, the playable house, Save & Quit and
loading the saved Sim after a full process restart.**

[Download the tested APK](https://github.com/Russianranger/s3ce/releases/download/v0.1.10-character-creation/S3CE-0.1.10-character-creation-arm32.apk).
Install over the existing S3CE app without clearing data. Leave **Original
rendering (diagnostic mode) unchecked**. To access reports, press Home and open
the app icon, then choose Save report. The permanent Report overlay was removed
because it covered an original character-creation control.

Current source work and acceptance requirements are recorded in
[AGENTS.md](AGENTS.md) and [the handoff](docs/HANDOFF.md).

## Supported candidate configuration

- Android 13–16 **with 32-bit ARM application support and 4 KiB memory pages**.
- Primary target: AYN Thor Max, Android 13 / Snapdragon 8 Gen 2.
- Self-contained game assets; no account, game-data download, or network permission.
- Touchscreen gameplay. No new controller mapping is implemented in this candidate.
- Separate application ID `io.github.russianranger.s3ce`; installs alongside the original.

This is **not a universal ARM64 port**. The original consists of an ARM32 Airplay
ELF loader and an ARM32 proprietary S3E program. ARM64-only and 16 KiB-page
devices are unsupported by this build. Android-version coverage is a target,
not a claim of successful gameplay on all four versions.

## Compatibility changes

- New native shim loads the exact supplied engine, resolves its ARM relocations
  before making engine text executable, and provides obsolete ARM EABI/C++ imports.
  Android's system linker loads only the new, text-relocation-free shim.
- Only the engine's dedicated executable-code allocation/free functions are
  redirected. Ordinary heap allocations stay non-executable. The old S3E program
  still requires a writable/executable code region; target SDK 28 is intentional.
- Private files storage replaces the optional shared-storage root.
- Contacts, location, and phone services return unsupported results; their
  permissions and the internet permission are removed.
- Screen wake uses the public window API instead of privileged `userActivity`.
- A separate launcher can save, share, view and copy report files after a game
  crash. Reports include available Android exit/tombstone records and Java exceptions.
- Original audio, textures and all other game assets remain byte-identical.
  Guarded configuration changes enable the existing Android GL/stack path;
  a fingerprinted native instruction correction preserves UI projection depth.
  Assets stay uncompressed for the original `AssetManager.openFd` audio path.

## Verified progression and limits

The device GPU trace identified high-resolution scaling that multiplied UI
projection depth by 3.375, placing sprites outside the visible depth range.
The guarded native correction fixes the projection Z scale at 1 and preserves
XY rendering and input coordinates. Original game assets are restored after the
unsuccessful 0.1.9 indexed-quad experiment.

The exact release APK was tested on Android 11/API 30 Google APIs x86 with ARMv7
translation, Emulator 31.1.4/KVM/SwiftShader, 4 KiB pages and 1920×1080. Actual
screenshots show appearance controls, female hairstyle changes, five traits,
name Alex, the house with full HUD, Save & Quit, and the saved female Sim loaded
in a new process with responsive gameplay. The earlier female-customization
crash did not recur in this tested path; its original invalid-object cause is
not established. No new physical Thor or Android 13–16 playthrough is claimed.

[Runtime evidence and screenshots](docs/RUNTIME_ACCEPTANCE.md) records the
required acceptance checkpoints. The final automated run remains red because a
redundant OCR step timed out after the successful save/load and interaction
checkpoints; those checkpoints passed manual screenshot/log review. This is
not an all-green automation claim.

## Build

Requires Linux, Python 3.11+, a full JDK 17+, Android SDK platform 35/build-tools
35.0.0, NDK r28c, and Apktool 2.12.1. Obtain the original APK separately; the
version-specific input SHA-256 is
`d42d0bf4a663abc3b1bb2abd0b350d93b6a2fa687a3b902f111a40c38a94f0d0`.

Create a private signing JSON with `password` and `alias` fields; keep it and
the keystore outside the repository. Retain the same key for install-over updates.

```bash
python3 scripts/build.py \
  --input /path/original.apk --apktool /path/apktool.jar \
  --sdk /path/android-sdk --ndk /path/android-ndk-r28c \
  --jdk /path/jdk-17 --keystore /private/s3ce-release.jks \
  --signing-json /private/signing.json
```

The build guards the input digest and exact patched methods, cross-compiles the
shim with warnings as errors, assembles the original Java bridge plus a new
launcher, signs v2/v3, and checks every original asset and ELF invariant.
See [validation](docs/VALIDATION.md) and [analysis](docs/ANALYSIS.md).

The repository's new compatibility code does not grant rights to the original
game, its engine, or its assets. Original notices remain with their owners.
