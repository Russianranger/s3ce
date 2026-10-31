# S3CE — The Sims 3 Android compatibility project

Experimental preservation build of the user-supplied Android game, using
[Russianranger/rea](https://github.com/Russianranger/rea) to inspect its original
Java/JNI bridge. **The Thor now reaches Create-a-Sim with room/hair textures.
Reopening now works too. The 0.1.8 report confirms callback delivery and drag
recognition. The game is waiting for the welcome hint's confirmation control,
which is invisible in the supplied screenshot. Advancing that hint on the Thor
is the next device check.**

[Download the APK](https://github.com/Russianranger/s3ce/releases/tag/v0.1.8-gesture-trace)

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

The latest Thor report shows both registered callbacks delivering input, the
game draining its input queues, and successful drag recognition. Its active
state is the welcome hint (12), before character rotation (13). The original
code ignores swipes in that hint and advances only after its confirmation
control emits an action. A tap on the message body does not confirm it.

Use the current 0.1.8 APK with **Original rendering unchecked**. At the welcome
hint, try a clean tap near **(500, 370)** on the 1920×1080 screen: approximately
26% from the left and 34% from the top, beside the hint's upper-left corner.
This is the source-derived area of its invisible round close/confirm control;
the exact vertical center depends on text layout. Release and wait one second,
then drag the Sim left/right. If the hint stays, use Report → Save report while
that run remains open. See
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
