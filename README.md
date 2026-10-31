# S3CE — The Sims 3 Android compatibility project

Experimental preservation build of the user-supplied Android game, using
[Russianranger/rea](https://github.com/Russianranger/rea) to inspect its original
Java/JNI bridge. **Release 0.1.9 still hides the HUD and a later female-Sim
interaction crashed. An unreleased correction now fixes the source-proven UI
projection-depth error. The next APK is withheld until visible controls and
progression through character creation into gameplay pass a full Android run.**

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
  Guarded changes enable the existing Android GL/stack configuration and replace
  one shared HUD strip's implicit indices with equivalent explicit indices.
  Assets stay uncompressed for the original `AssetManager.openFd` audio path.

## Latest update and Thor test

The latest device GPU trace shows the UI being clipped: high-resolution screen
scaling multiplies projection depth by3.375, putting HUD sprites at normalized
Z1.6875 outside the visible range. The guarded correction changes only the
projection scale's Z argument to1. Captured device matrices and original sprite
art reproduce blank output before the correction and visible sprites afterward;
XY/input coordinates remain identical.

The unsuccessful indexed-quad experiment is removed from the build; original
assets are restored. A separate crash at game offset13b784 involves an invalid
Group/World cast object. Its origin is still under investigation. Internal
Android runtime testing is in progress. No new APK is ready for presentation.

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
