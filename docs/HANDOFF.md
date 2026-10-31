# Development handoff — 0.1.8

The Thor now reopens successfully. Preserve the working RAM, graphics, stack and
cache-flush fixes. Swiping at Create-a-Sim remains unresolved.

The 0.1.7 report shows touchscreen source0x1002, ID0, text gate false, fourteen
DOWN/UP pairs and 283 MOVE events with substantial horizontal deltas. Native
primary/pending fields update and frames advance. Published polling fields stay
zero because the game registers callbacks and never imports the polling API.
Do not inject PointerUpdate or duplicate synthesized single-pointer events.

Actual original ARM queue/callback execution works; absent event1 registration
reproduces taps without movement. The game's real adapters, two input buffers,
frame consumer, drag threshold, state3 gesture tick and CAS rotation math work
at low/high code and separately relocated data addresses. No hidden tutorial
acknowledgement, hitbox, float ABI or timing gate was found.

0.1.8 adds a bounded observer of registration and actual callback entry/return.
Its proxy must use the generic Int32 stack gateway, then the original callback
gateway for the unchanged game callback. Fast switching breaks nested stack
bookkeeping. Duplicate registration, unregister, reentry, permanent generation
failure and slot exhaustion must preserve original behavior. Slots are never
reused. Game-state snapshots are read only after strict source/literal/vtable
validation and safe reads; split data is not codebase+preferred-global-offset.

Next hardware gate: install over the existing app, Original rendering unchecked,
reach CAS, drag left/right a few times and immediately save the same run's report.
Look for event1 REGISTER, ENTER/EXIT and queued counts/Scene gesture state/menu
state13/CAS angle. The last snapshot is after callback enqueue, before a later
frame may consume it; interpret that timing rather than equating a queued event
with final rendered rotation.

Final APK SHA5889dd74a5094603e78534fcde915590ae1cb87d45c7f0252eb5fa4d51d0143a;
shim SHA3b9397d65bafe7921185b48390183bbd006004bfd18dcf37dc50b4c990ac7912.
Eleven sanitizer suites, eighteen compiled ARM proxy scenarios, independent
review,310-method static DEX analysis and APK build/signature checks pass.
Publication receipt pending. Same app ID/key/data. All full user reports and
signing material stay private.

## Historical 0.1.7 handoff

Published source `9a6c82ef217a4a206c73592dc12b9df67adf93d4`.
Publication/download-verification run `41156929416` passed.

0.1.6 reached Create-a-Sim on the Thor with room/hair textures. Preserve its
StackSwitch=1, complete veneer flush, PVRTC adapter and real-context safety.
User still cannot swipe. Fresh subsequent processes show the early native
insufficient-memory dialog before S3E allocation; old0.1.5 tombstones are stale.

0.1.7 replaces exact get_mem_info223b9: the old MemFree%d→LSL10 signed32 bytes can
be negative/zero for multi-GiB free RAM. DeviceGetInt6 then fails the signed64KiB
preflight. Actual old ARM instructions reproduce those errors. New parsing uses
uint64 KiB and saturates to INT32_MAX; real low/zero and unknown-1 are preserved.
The failing device's actual MemFree was absent, so inspect the new raw/capped RAM
log before attributing any later allocation failure to this overflow.

No input behavior change: native ARM execution shows consistent4/5/6 events
synthesize single0/1 callbacks for the game, with valid sparse IDs. New Java
source/action/ID/text-gate totals and actual JNI primary/pending/published traces
will locate the device failure. JNI row457d8, fnword457e0 is exactly guarded; the
original is called once. Reports retain128KiB native text, others32KiB. Unsynced
state snapshots are observations, not engine-lock synchronization.

Next hardware gate: enter CAS, drag from the Sim torso left/right, save that run's
report while stuck; then close/reopen once and save another report if memory
warning returns. Distinguish Java-gated events, actual native ID/type/coords,
primary-ID selection and pending-vs-published movement. Avoid duplicating primary
single-pointer events or altering graphics based on a gesture symptom.

Final APK SHA202e92142bbaca64ed769a06df21e7b5f6609470330432a4d34d1def670c85fb;
shim SHA215636395d2e539db5f06e23815ccb38d6b4877660a941b4a76d1c8f9ec3897e.
Eight native sanitizer suites, original ARM RAM/pointer proofs, independent
review,310-method DEX analysis, actual assembled touch wrapper tests and final
build/signature/reconstruction and independent publication/download checks pass.
Same app ID/key/data.
Full user reports and signing material stay private.

## Historical 0.1.6 handoff


Published source `1b9e216947939308327287bb76decbd035829938`.
Publication/download-verification run `41155065375` passed.

0.1.5 still crashes on the Thor. Its fresh/cached method IDs match, but both
CallVoidMethodA and the static Java logger throw before Java body entry. Do not
continue blaming method identity or Java code inside glInit based on that report.

The game always runs on a heap fibre: ExecStartGame1946c -> FibreCreate2e73c ->
FibreSwitch_asm2e4a0(MOV SP,R0 at2e4b8). mymain194d0 records the original OS stack
in g_LoaderStack56758. StackSwitch=0 only disables API/callback veneers. Exact
ART13 source rejects managed entry below Thread::GetStackEnd; foreign-SP rejection
fits both pre-entry failures, but the report did not capture the Throwable type.

0.1.6 enables original StackSwitch=1 for Android and routes lazy GL initialization
through the original generic stack thunk when necessary. Native thread identity,
current EGL context, original Java lifecycle, app ID, signing key and data remain.
The generated veneer arena is inside the dedicated executable allocation; ensure
its full range is flushed because original rounded-core flushing misses its tail.
Native-only Throwable classification and pthread stack bounds must stay available
when calling a Java logger is impossible.

Final native SHA500525a6fe3a2f382f8445aa1ed13b91cbc2b7fc9ff5478ff537f5bcdfb75025;
APK SHA3b7b82da9ed56a8c0c2cf9afb0abd4c653eb1a1c63ebb04f774d5b0f7d726cd8.
Six native sanitizer suites, eight compiled ARM bridge scenarios, independent
review,309-method DEX analysis and build/package/reconstruction checks pass.
Publication/download verification passed. Actual Thor startup,
textures, swipes and save/reopen remain the next hardware gate. Full reports and
private signing material stay private.

Next-report markers: allocation must log StackSwitch=1; the expanded code flush
must cover the entire tracked mapping including its generated veneer tail; the
stack bridge must report SP inside the current pthread stack before JNI. Java
GL ENTRY -> original glInit/createView(gl=true)/EGL -> EXIT then establishes the
next startup gate. If it fails earlier, use the native Throwable summary and
SP/bounds rather than trying another Java-only logger. Do not increase StackSize
as a substitute for restoring a foreign stack.

## Historical 0.1.5 handoff


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
