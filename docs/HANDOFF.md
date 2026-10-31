# Development handoff — 0.1.5

Published source `c508de5dacb8ee0a0c41eecf0a29926d63bd7447`.
Publication/download verification run `41152986602` passed.

0.1.4 still fails on the Thor: callback returns with EGL_NO_CONTEXT/EGL_SUCCESS
and no Java GL-entry log. Its post-call JNI exception=0 was not conclusive,
since the original callMethod describes/clears exceptions internally.

Independent original-Thumb execution and ABI/assembly review confirm cached
Thread reference+8, glInit(I)V ID+14, CallVoidMethodV slot0xf8, arguments, pointer
Thumb bits and 8-byte stack alignment. No static dispatch defect was found.

0.1.5 replaces that initial dispatch with a fresh public compatGlInit(I)V lookup
and CallVoidMethodA. The Java wrapper invokes the untouched/hash-guarded private
glInit directly, records durable lifecycle state/full failure stack, and rethrows
the same exception. Do not remove its original unlock/UI/surface/relock protocol.
Typed startup must return without an exception and with a real current context
before old s3eGL_start is used for its own bookkeeping. The shared GL guard,
configuration, texture/input/report changes and install identity/key remain.

Next device evidence must inspect compat-java-gl.log entry/exit/FAILURE and native
typed-call markers. The exact prior device-side dispatch cause remains unknown;
host mocks do not establish successful EGL startup or gameplay. Publication and
build receipts are recorded in VALIDATION.md. All native sanitizer suites,
original Thumb dispatch/exception proofs, actual wrapper DEX/Java logger tests,
309-method static DEX analysis, ARM/import/relocation/asset/signature checks and
byte-exact release reconstruction pass. APK SHA-256:
69d26e8f6d96d67b64c2366811e9ed796231d9919ac2076a6c3c87d9bdc543db.
Full user reports stay private.

## Historical 0.1.4 handoff


Published source `a410d920d57af7f4dce926f7742028f1a51e9111`.
Publication and independent download verification passed in run `41150906072`.

0.1.3 avoided the original platform glGetString crash but returned NULL for
pre-context Vendor/Renderer/Version/Extensions. The new report then crashed in
the game's unchecked string length code at S3E PC+0x1134. Do not return NULL or
invent capability strings for those game startup queries.

0.1.4 lazy-initializes the REAL game-window context via original s3eGL_start
Thumb 0x210a5 on the running engine thread. JNI state at 0x53af0 must match that
thread; fields+8/+14/+10c provide thread/method/lock prerequisites. Original
AirplayThread.glInit provides the correct unlock/UI-view/surface-wait/relock flow.
Calling Java glInit before runNative would unlock an unowned engine mutex, so
that alternative remains invalid. No temporary pbuffer context is used.

After initialization, require current EGL context AND no pending JNI exception;
then obtain actual driver/adapter strings. Recursion/failed initialization
records an explicit EGL/JNI abort message before termination. Root report export
works and now includes AirplayGL/AirplayView/System.err/EGL output for this path.
Keep original driver dispatch 0x55a64 and original extension filtering intact.
The existing Android GLForceDLLVersion 0x0101 override stays for the GLES1.1 path.

All native/host/binary/packaging checks passed. Thor confirmation remains pending.
Next test: install over 0.1.3, leave original-renderer option UNCHECKED, Start game,
menu/backgrounds/hair/eyes, CAS swipes, then house and save/reopen. On failure,
read the new initialization markers and EGL/JNI abort details before patching.

Preserve the same app ID/key/data, original JNI classnames, ARM32/4KiB/target28
constraints and private signing backup. Full device logs stay private. Release
publication uses the pinned 0.1.0 base APK and byte-exact literal reconstruction.

## Historical 0.1.3 handoff


Published source `4a4e138e6a13f796355d20658cef754e3e790530`;
publication/download-verification run `41149513664` passed.

Reports now save correctly. The attached 0.1.2 report identifies a real native
crash in platform glGetString(GL_VERSION), fault nearNULL, from original runtime
wrapper returnoffset 0x33987, in both rendering modes. Startup had only the
software view; JavaGL initialization had not run. Do not revert Java/input or
PVRTC changes based on that trace: the failure is the earlier version query.

0.1.3 selects existing [S3E] GLForceDLLVersion=0x0101 on Android, skipping the
engine's early version probe. It also replaces original wrap_glGetString with a
current-context guard. The correct driver slot is g_glGetString 0x55a64, derived
from its own tablebase55a44, NOT the separate version-state table55a04. The
verifier checks instructions, literal, symbol, RWsegment and entry fingerprint.
Do not conflate those adjacent legacy tables in future patches.

Shared guard remains active in original-renderer mode; only the texture adapter
is bypassed in that mode. No UI-thread EGL context creation or synthetic vendor/
extension strings were introduced. The engine's original extension filtering
is preserved and NULL is handled before string access.

Next Thor gate: install over 0.1.2, UNCHECK Original rendering (the user last
selected it), Start game; menu, backgrounds/hair/eyes, CAS room and swipe tutorial,
then house/save/reopen. On failure, Save report again. Full game/runtime success
is not yet claimed. All report export and crash-capture features remain.

Keep same app ID/key/JNI classnames. ARM32,4KiB,target28 and RWX S3E code constraints
remain. Never publish the private signing backup. Release publication uses the
pinned 0.1.0 base APK plus byte-exact literal reconstruction.

## Historical 0.1.2 handoff


Published source: `1f2805317582e2d7cefa5a8145cb1b59c9643424`.
Publication/download-verification run `41147877179` passed. APK and instructions
are available on release `v 0.1.2-crash-report`.

0.1.0 reached the menus/Create-a-Sim with missing graphics and stalled swipes.
0.1.1 added PVRTC fallback + input fixes + separate report launcher, then crashed
at startup on the Thor. Its plain EXTRA_TEXT sharing could not be saved by the
file manager, so no exact crash trace is available yet. Do not claim a confirmed
startup-crash fix.

0.1.2 adds direct SAF Save report, real attachment sharing, view/copy, Java crash
capture, retained own-package exit history and readable native tombstone summary.
The user should save a report BEFORE starting the game, since Android may still
retain the previous 0.1.1 failure. Provider and launcher both use :launcher; do
not move file serving into the potentially hung game process.

The extra alpha-state config from 0.1.1 is rolled back as an unnecessary risk;
all original assets/config are identical again. PVRTC software support remains.
Native configureGraphics(false), selected by Original rendering diagnostic mode,
bypasses GL hooks and uses the original platform dlsym path. This isolates the
new rendering adapter; it is not an ARM64 port or a separate game implementation.
Mode changes require the existing runtime/process to be closed. Keep the JNI
configure call before bootstrap; bootstrap/export class is GameBootActivity.

Native audit ruled out the hypothesized stack-alignment and missing-resource
path branches for the examined call sites; all 691 texture mip levels passed
sanitizers. Do not implement speculative assembly thunks or resource aliases
without new evidence. Next step is the actual device exit/tombstone + logs.

ARM32/4 KiB/target28 remain deliberate. Dedicated S3E code is RWX. Preserve app ID,
original JNI class names, and the key from private S3CE-private-signing-backup.zip
for install-over updates. Never commit the key or its signing configuration.

Publication reconstructs the signed APK from the pinned 0.1.0 release's unchanged
ZIP data plus a small literal payload. Complete APKs remain in Releases.
See RELEASE_NOTES.md and VALIDATION.md for user steps and exact verification.

## Historical 0.1.1 handoff


Published candidate source commit: `8a64cb4e985702150e1d9f2169a80e71239a71d8`.
Publication and independent download verification passed in run `41146391540`.

0.1.0 reached the menu and Create-a-Sim on the Thor but had white backgrounds,
missing hair/eyes, and a stalled swipe tutorial. No gameplay/save gate passed.
0.1.1 adds software PVRTC support, the existing Snapdragon alpha configuration,
indexed/cancel-safe touch dispatch, and a resume lost-wake correction.

Next meaningful gate: install over 0.1.0; verify menu/room/hair/eyes; swipe across
the Sim and advance the tutorial; enter the house; check audio/touch and save/
reload. Do not claim these have passed until the user provides results.

Diagnostics: app icon opens CompatActivity in :launcher and its own reports
task; Start game enters GameBootActivity in the main process, bootstraps JNI,
and opens original Main. A Report button is attached after every game view
replacement. If game UI blocks, Home -> app icon -> Share diagnostics accesses
persisted logs independently. Do not auto-start the game from the launcher.

Native log includes GL renderer/extensions, bounded upload/errors, and mapping
addresses. Java log includes touch arrivals, returned swap/canvas frame counts,
UI heartbeat age and stalled thread snapshots. A returned swap is not proof of
successful frame presentation. Native callbacks remain synchronous.

ARM32 support, 4 KiB pages, and target SDK 28 remain deliberate constraints.
Dedicated S3E code mappings remain RWX. Do not raise target or advertise ARM64/
16 KiB support without new runtime work and device validation.

The exact original APK is required to rebuild. Keep the signing key from the
separately saved private S3CE-private-signing-backup.zip for install-over updates;
never commit it or its configuration/password. App ID and original Java/JNI
class names must be preserved.

New release publication uses pack_release_delta.py plus assemble_release.py:
unchanged ZIP data is copied from the hash-pinned published 0.1.0 APK and changed
bytes are staged as a small literal payload. Reconstruction must match the
signed new APK hash exactly. Full installable APKs are published to Releases.
See VALIDATION.md, native/README.md, and patches/README.md for precise test scope.
