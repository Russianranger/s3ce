# S3CE — The Sims 3 Android compatibility project

Experimental preservation build of the user-supplied Android game, using
[Russianranger/rea](https://github.com/Russianranger/rea) to inspect its original
Java/JNI bridge. **The latest trace showed that returning NULL from early GL
queries crashes the game itself. Version 0.1.4 creates the real game-window
context through the original engine initializer before those queries. Thor
confirmation is pending.**

[Download the APK](https://github.com/Russianranger/s3ce/releases/tag/v0.1.4-egl-startup)

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
- All original game/audio assets remain byte-identical except for a guarded Android GLES-version setting, and stay uncompressed, as
  required by the original `AssetManager.openFd` audio path.

## Latest update and Thor test

Version 0.1.4 invokes the original window-context initializer on the game thread
before capability queries, preserving the engine's native/UI synchronization.
It requires a real current EGL context and clean JNI state before driver calls.
This replaces 0.1.3's incomplete NULL-return behavior. No temporary rendering
context or invented capability strings are used.

Install over the existing app, leave **Original rendering unchecked**, and press
Start game. Check menu/backgrounds, Sim hair/eyes, room textures, and swipes.
On failure, reopen the app icon and Save report. See
[test instructions](docs/RELEASE_NOTES.md) and [native details](native/README.md).

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
