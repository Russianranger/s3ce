# Current continuation — 0.1.13 camera-input candidate

Recovered live main at `4ea1ecd6b93c65b84078a1c0e653b5e25da37cb0` before editing.
Following 0.1.12, the user reports everything seems to work except the bottom-right
icon, intercepted by an oversized camera-pan touch region. No fresh diagnostic
is attached; version112 is inferred from context. Do not infer a repeated-start
count or certify memory reliability from this general positive report.

Original camera hit testing runs before plumbob/Wishes. Its scaled pixel radius
is compared with logical touch; earlier fixtures left this camera region zero
and disabled. Investigate all field consumers, preserve camera drag/release, and
extend the original ARM checks to real active/expanded camera states. Keep global
XY, existing HUD/context-menu fixes, saves and compatibility behavior.

Candidate0.1.13-camera-input / code113 is signed with the existing key,
76,770,649 bytes, SHA256
`ce8c54bffe5deeb00e6c81b3d942bfdd5f5480b63ef281d33b053cc255eb3a5e`.
The one-instruction camera correction and expanded tests are documented in
[PAN_HIT_TEST.md](PAN_HIT_TEST.md). Original bridge/launcher DEX are unchanged.
All15 native sanitizer suites,20 ARM cases (800 camera comparisons/480 boundary
checks plus180 prior HUD comparisons),22 runtime tests, source/asset/signature
checks and exact release reconstruction pass. Read-only observer fields now
identify actual phase/flags/camera state; their timing is not final-action proof.

Next: push exact candidate to Android validation, two menu cold starts plus
normal creation/save/reload prefix, then prioritize camera toggle/drag/release
and bottom-right selection with actual state evidence. Publish these exact
bytes after review and deliver a short install-over test.

# Current takeover — 0.1.12 HUD/startup candidate

Recovered `main` at `a13b0ec799adca78edeac8ea56e69ac53c60a669` against live GitHub
before editing. Reused original input, signing identity and prior analysis.
Complete user reports and signing material remain outside Git. The report
confirms installed 0.1.11, Thor/API 33, a 32-bit process and normal rendering.

The user physically confirms several object actions and previous-save loading.
Earlier UI, creation, house entry, walking, saving and camera zoom/pan remain
preservation requirements. Remaining: the first start failed, retry succeeded,
and circled HUD targets appear offset or inaccessible. The 1920×1080 screenshot
circles the left status panel, chair/Buy above Pause, and wishes/plumbob panel.
See HUD_INPUT.md for exact identities and geometry. Preserve global XY and the
accepted object-menu anchor.

The report records a post-install LOW_MEMORY exit: PID 25490 at 13:12:07 CDT,
reason 3/status 0, after the 13:11:56 install and before successful PID 26391
at 13:12:10. This is the strongest match for the failed start. Its peak footprint
is absent (rssKB=0), and the successful retry overwrote earlier boot/native logs.
The retained native SIGSEGV at 07:41:31 predates this install. The historical
emulator translator abort is separate. Android SDK confirms LOW_MEMORY=3 and
EXIT_SELF=1. Do not conflate these records.

Candidate 0.1.12-hud-startup / code 112 is built and signed with the existing
certificate, 76,770,649 bytes, SHA256
`b73c15341acbb61e7fa85173eb440650c665a65df57ce1ac46caf0e2d7325b64`.
All 15 native sanitizer suites, 20 HUD ARM cases/180 dispatch comparisons,
20 original context-menu ARM cases, assembled input/audio/surface/session DEX
checks, 348-method static DEX analysis, host retained-session tests and byte-exact
release reconstruction pass. APK assets, ARMv7/4 KiB/target 28, package and signing
identity are verified. These are host checks, not new Android gameplay evidence.

[Run 41230641948 attempt1](https://github.com/Russianranger/s3ce/actions/runs/41230641948)
is green. Root and two reviewers inspected the complete hash-verified archive:
four rendered menu cold starts, zero failures; ordinary creation/save/restart/load;
visible status and Build controls; completed Bed Sit; post-action save and clean
normal native Quit. Full log has zero fatal/ANR and zero late-audio warnings.
See [runtime receipt](HUD_STARTUP_RUNTIME_ACCEPTANCE.md) and its evidence index.
The original automated gate_passed=false remains intact; separate manual decision
allows this exact targeted Thor test candidate. No rebuild or resign is needed.

Limits: runtime save was candidate-created; prior0.1.11 save install-over remains
Thor validation. Wishes activation was not demonstrated: source-proven coordinate
repair remains, but runtime reached original tutorial gating/Go to Town hint.
New Home/return and physical memory-pressure reliability remain unconfirmed.
This is API30 x86/ARMv7 translation, not physical ARM or Android13–16 acceptance.

## Publication verified — next action is the Thor test

[Release v0.1.12-hud-startup](https://github.com/Russianranger/s3ce/releases/tag/v0.1.12-hud-startup)
was published from `a448fa22123e1a0bd5cd0e46ce046a17d9696a95` by
[run41234504645](https://github.com/Russianranger/s3ce/actions/runs/41234504645).
Reconstruction, original certificate, package/code112/target28, publication and
download checksum checks passed. An independent public download also matches
76,770,649 bytes and SHA256
`b73c15341acbb61e7fa85173eb440650c665a65df57ce1ac46caf0e2d7325b64`;
its v2/v3 signature, original certificate, ARMv7 and version name were rechecked.
These are the exact tested signed bytes; no rebuild or resign occurred.

[Direct APK](https://github.com/Russianranger/s3ce/releases/download/v0.1.12-hud-startup/S3CE-0.1.12-hud-startup-arm32.apk).
Install over the existing app; do not uninstall or clear data; Original rendering
unchecked. Use existing Thor save; test status/Buy/wishes/plumbob/Pause, one real
object action, walking/camera, save/reload, three additional force-stop/restarts
and Home/return. Export Home→app icon→Save report after a failure and retry.

The user-facing delivery includes direct APK, alternate release route, identity,
checksum, implementation/validation limits and short test. Work is now waiting
for the user's Thor report/screenshot; continue refinement from this source.


# Development handoff — 0.1.11

ROOT delivery gate PASSED for C3, 76,762,457 bytes, SHA256
`3f7698294ace0e7a78bb32524811ae237701395dc87184102cdc4c47534d07f5`. VersionCode 111,
same package/key/private-data location, ARMv7/4 KiB/target SDK 28. Install over the
existing app; Original rendering unchecked. Frozen bytes reconstruct from
.publish/v0.1.11-object-actions without rebuilding or resigning.

Actual run 41215805134 attempt 2 / source 02b1375300f541f3d092b3d1720d16031f4b7a06
completed female creation, five traits/name Alex, house gameplay, normal save,
new-process saved-Sim load (PID4010→11395), visible Chair Sit followed by a seated
pose, another normal save, and main-menu Quit→native Main return→Activity.finish
→Compat launcher. The complete run has zero fatal/ANR matches and no late-audio
warning. Root and two reviewers accepted the raw frames/full archive. Original
automated gate_passed=false remains intact; manual signoff is recorded separately.
See [durable receipt](OBJECT_ACTIONS_RUNTIME_ACCEPTANCE.md) and its JSON index.

Three targeted corrections: context-menu bounds now use original Display Y
anchoring; CacheGLES destruction follows existing DLC/image cleanup; six guarded
SoundPlayer methods serialize callback/lifecycle ownership and reject retired
track callbacks before JNI. Native bytes and original assets are unchanged from
C2; only the audio bridge DEX and signing records changed. The 14 native sanitizer
suites,20 context-menu ARM cases, 16 shutdown ARM cases, audio DEX lifecycle/race
regressions, old-C2 counterexample, six method guards and310-method static DEX
analysis pass. Android/native audio services remain host fixture boundaries in
those race tests; the actual accepted run supplies gameplay and Quit evidence.

C2 was rejected on a late queued SoundPlayer null-track write after native Quit.
C3 attempt 1 aborted pre-UI in the emulator ARM translator's VADDL alignment check;
its exact cause remains unproven and those exact bytes passed attempt 2. Preserve
both failures. The test environment is API 30 x86/ARMv7 translation, not native
ARM hardware or new Android 13–16 acceptance. Sofa and C3 Android Home/resume were
not directly exercised; the controller cannot safely follow Home's portrait
orientation with its retained landscape viewport. The earlier female crash's
invalid-object root cause also remains unresolved; no generic skip was added.

Unattended runtime CI now stops after the established creation/save/reload prefix;
frame-guided object/Quit review is opt-in. Source checkpoints and publication of
these exact accepted bytes are authorized; future APK edits need affected checks.
Keep keys and complete user reports outside Git.
## Publication verification

Release [v0.1.11-object-actions](https://github.com/Russianranger/s3ce/releases/tag/v0.1.11-object-actions)
was published from source `c7fee029f5ee6fcda3383d5baabaea6e3d337c9c`.
[Publication run 41219026998](https://github.com/Russianranger/s3ce/actions/runs/41219026998)
passed byte-exact reconstruction, signature/package/version111 checks, prerelease
upload and download/checksum verification. A separate public GitHub download
also matched 76,762,457 bytes and SHA256
`3f7698294ace0e7a78bb32524811ae237701395dc87184102cdc4c47534d07f5`.
This is the exact manually accepted C3 APK; no rebuild or resigning occurred.


# Historical handoff — 0.1.10

The user delivery gate PASSED for the exact frozen release APK. Actual Android
execution shows restored UI, female customization with three hairstyle changes,
Home/reopen in the same process, five traits, name Alex, confirmation into
SceneGame, a rendered house/full HUD, normal onboarding dismissal, Save & Quit,
and loading the existing saved female Sim in a new process with live input.

APK: S3CE-0.1.10-character-creation-arm32.apk, 76,762,457 bytes,
SHA256 45335ca99a15e2b26dcbaeb0547cb2edc184eb7fa302446abae22dd455fb40fb.
VersionCode110; package io.github.russianranger.s3ce; same signing certificate
and private-data location as previous releases. Original rendering stays off.

[Durable runtime evidence](RUNTIME_ACCEPTANCE.md) records screenshots/hashes,
source revisions, process IDs4210→15467, persistent sim3dat0/settings files,
and zero fatal/ANR log matches. Runtime: Android11/API30 Google APIs x86 with
ARMv7 native translation, Emulator31.1.4/KVM/SwiftShader, 4KiB pages,1920×1080.
No physical Thor or new Android13–16 gameplay claim. The CI11 workflow remains
red from a redundant final Tesseract timeout after all required save/reload/live
interaction checkpoints; root and two independent reviewers accepted those
actual checkpoints. Preserve the automated failure and manual acceptance.

UI cause: captured Thor GPU matrices put HUD vertices at NDCz≈1.6875 because
scale3.375 affected Z. Native ui_depth.c changes only game+0x135d80 from
MOVr2,r0 to MOVr2,#float1 within final projection wrapper135d50. A116-byte
fingerprint, tracked allocation lock/bounds and original full instruction-cache
flush guard the patch. XY/input and outside-UI/legacy scale1 are unchanged.
Native SHA19c6bf2c89800590a316c2eaa8245159a021be3df6ac2dcc4d35037cf166330c.
Original assets are restored; historical ui_indices experiment is not applied.

The permanent Report overlay was removed because it overlapped the real CAS
control. Reports remain available through Home→app icon→Save report. Existing
PVRTC, RAM saturation, native-stack/code-flush/input/lifecycle fixes remain.
NativeTombstoneSummary adds bounded crash-thread registers (61 regressions).
Twelve sanitizer suites,32 original ARM projection cases, sprite replay, actual
assembled touch/lifecycle/GL regressions and310-method DEX analysis passed.

The original female-selection crash at13b784 dereferences a corrupted vtable
word4 in Group/World cast13b774; actual caller return is atSP+4. Exact male and
female parsing/clone/destruction/replacement/skinning and RNG fixtures do not
reproduce it. No generic NULL skip/model replacement was applied. It did not
recur in the tested female path; its underlying origin is unresolved. See
CHARACTER_CREATION_CRASH.md for proof boundaries and exact source references.

Build in isolated --build-dir/--dist-dir paths. The release transport reconstructs
the exact tested signed APK from the pinned0.1.0 base and485945 literal bytes;
no rebuild or re-sign is involved. Keep keys and complete user reports private.

## Publication verification

Release [v0.1.10-character-creation](https://github.com/Russianranger/s3ce/releases/tag/v0.1.10-character-creation)
was published from source `3b2ba52972225f6bf6963fe3c0361775090e5f8d`.
[Publication run41179968392](https://github.com/Russianranger/s3ce/actions/runs/41179968392)
passed byte-exact reconstruction, signature/identity checks, prerelease upload
and independent download/hash verification. A separate public download also
matched 76,762,457 bytes and SHA256
`45335ca99a15e2b26dcbaeb0547cb2edc184eb7fa302446abae22dd455fb40fb`.
This publication workflow success is separate from the manually accepted Android
runtime checkpoints and the preserved CI11 final OCR failure.

## Historical 0.1.9 handoff

The Thor now passes the original hint confirmation and rotates/customizes the
Sim. Input is working. Current blocker: missing M3G HUD sprites/panels/icons;
fonts, standalone PNG hand buttons and3D room/models render. Preserve all RAM,
stack, texture and touch fixes.

0.1.9 is a narrow graphics compatibility candidate, not a confirmed device fix.
It changes the one anim2d.m3g strip shared by530 sprites from implicit first0/
length4 to explicit0,1,2,3/length4. Source ARM captures show the intended change
is only DrawArrays→DrawElements; host pixel comparisons are identical. No texture
filter/material workaround is justified by the available evidence.

patches/ui_indices.py accepts only the pinned original or exact patched res.dz.
It modifies TSA object5, fixes required header/section lengths/Adlers, and does
ordered LZMA stream replacement. All677 other compressed and decoded entries
remain identical. Never use nonmonotonic append-retarget offsets without proving
legacy reader semantics. scripts/verify.py checks exact expected archive/config.

The native GPU witness is read-only, shape-scoped and bounded to25 snapshots.
It captures arrays/units/binding/filter/caps/color/viewport and three matrices;
no GL state is changed and no client/index pointer is read. Error flags are
preserved. UI GPU labels identify matching quad shapes, not verified HUD assets.

Next Thor gate: install over0.1.8, Original rendering unchecked; inspect hint
panel/close control, appearance/clothing controls and traits. If still missing,
keep that run and save its report/screenshot. Compare live UI GPU state with
source-captured expectations before choosing another graphics change.

Artifact SHA67664a9f8490e0ccb28c1f83576b478ac99a1a48a958e69850e8c7cf97f4a344;
native SHA71bc072c1ef411542c6797e7c897a87d7df111a53814e3c234acdb3698ae0e67.
Published source `aca6af177e1f43644ef3a1cf5dee939b53297f2a`;
publication/download-verification run `41164717515` passed. Release
`v0.1.9-ui-rendering` size/digest match the frozen APK. Keep signing material
and full reports private.

## Historical 0.1.8 handoff

Latest device evidence: callbacks and drag recognition work. The game remains
in SceneMenu state12, the CAS welcome hint. State12 accepts logical event11
mask4/80 and advances13; it ignores tap gesture3 and drag5 directly. Its own
round close/confirm control must complete a clean click and its release
animation. The screenshot lacks this control and the surrounding sprite frame.
Do not keep treating this report as lost native motion or change input scaling.
Use the existing APK to check a clean tap around physical(500,370), approximately
26%/34% of the1920×1080 display, then wait one second before dragging. This is a
source/screenshot-derived target, not a hardware-confirmed result. Button radius
is35 scene units (about118 physical pixels); exact Y depends on wrapped text.
The invisible sprite UI remains a separate rendering investigation. Original
sprite assets contain visible pixels, and input/render scaling agree exactly.

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
Published source `583a18fb663e491992dd367cab2f6578bdabfbce`;
publication/download-verification run `41159924448` passed. Release
`v0.1.8-gesture-trace` asset size/digest match the frozen APK. Same app ID/key/data.
All full user reports and signing material stay private.

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
