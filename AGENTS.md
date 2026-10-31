# Current continuation — camera pan steals bottom-right taps

The user reports everything seems to work except the bottom-right icon: camera
pan captures a very large region of the lower-right screen. This follows the
0.1.12 delivery; no fresh report is attached, so installed version is inferred
from context. Preserve newly confirmed behavior.

Camera testing precedes other HUD selection. Prior fixtures left its real
radius zero and its enable bit off; extend coverage with enabled and expanded
states. Do not attribute this new physical interception to tutorial gating.
Correct the source-backed radius without shifting global XY or changing game
state. Validate the bottom-right action plus normal camera toggle/drag/release,
nearby world/UI targets, and preserve all saves/rendering/action fixes.
Continue through signed APK publication and concise testing handoff; prior
push/release authorization persists. Preserve ARM32/app ID/key/private data.

# 0.1.12 targeted test candidate — exact bytes accepted for publication

APK SHA256 b73c15341acbb61e7fa85173eb440650c665a65df57ce1ac46caf0e2d7325b64,
code112, existing certificate/package/data. Run41230641948 attempt1 is green;
root and two reviewers accepted all4 menu cold starts (0failures), normal
creation/save/restart/load, status/Build selection, Bed Sit, post-action save
and clean native Quit. Complete log has0fatal/ANR and0late-audio warnings.
See docs/HUD_STARTUP_RUNTIME_ACCEPTANCE.md and its JSON evidence index.

Publish only these frozen signed bytes; no rebuild/resign. Automated gate=false
is retained; separate manual decision authorizes this focused Thor test release.
Wishes-strip activation, prior0.1.11 save install-over, new Home/return and
physical LOW_MEMORY reliability remain unconfirmed. Do not claim those passed.
Published exact bytes as v0.1.12-hud-startup from a448fa22123e1a0bd5cd0e46ce046a17d9696a95;
run41234504645 and independent public download/signature/checksum verification pass.
Next is the user Thor test/report; see current handoff. Continue from new feedback.
Future APK edits require fresh affected checks. Keep private reports/keys out.

# Current assignment — Thor HUD refinement and startup attribution

User authorizes focused source/docs changes, commits/pushes and next test release.
Recover main, preserve later legitimate work, complete meaningful validation and
explicitly deliver the signed APK/testing handoff. Physical Thor 0.1.11 confirms
object actions and previous-save continuation; first-start failure/HUD taps remain.

Read docs/HANDOFF.md. Post-install Android reason 3 means LOW_MEMORY (EXIT_SELF=1).
Peak footprint is unknown. Do not equate it with the pre-install SIGSEGV or
historical emulator translator abort. Retain session evidence and account for
every cold-start attempt. Successful retry or reduced allocation is not a fix claim.

Use screenshot/original ARM geometry for narrow HUD changes, preserving global
XY and accepted object-menu anchoring. Distinguish host fixtures, Android runs,
physical observations and uncertainty. Future APK changes need affected checks.
If Thor is necessary, finish independent work and deliver a useful candidate,
clear limitations and short test.

Preserve app ID/key/data, ARM32/4 KiB/target 28, original assets, UI depth, camera,
saves, walking, actions, teardown order and audio ownership. Original rendering
stays unchecked. Keep keys/full reports outside Git; isolate build/dist paths.

# Current release — 0.1.11 object actions: gate passed

The user physically verified 0.1.10 UI, character creation, house, walking,
saving, zoom and pan on the Thor, then reported visible actions rejecting taps.
Exact C3 APK SHA256
`3f7698294ace0e7a78bb32524811ae237701395dc87184102cdc4c47534d07f5` (76,762,457 bytes)
passes the new real Android gate: visible Cheap Dining Chair / Sit selected,
Sim walks then sits, ordinary post-action Save and Quit, normal main-menu Quit,
native Main return, Activity finish and Compat launcher resume. Entire accepted
run has no fatal/ANR matches or late-audio warning. Root and two independent
reviewers inspected actual frames and the complete hash-verified archive.

Run 41215805134 attempt 2 / source 02b1375300f541f3d092b3d1720d16031f4b7a06 is green.
Its automated acceptance file retains gate_passed=false awaiting human visual
review; the manual decision is separately recorded in the durable receipt.
C2's late SoundPlayer NPE and C3 attempt 1's ARM-translator startup abort remain
preserved as failures. Do not describe all attempts as successful. Sofa itself
and C3 Android Home/resume were not directly exercised. Runtime is API 30 x86
with ARMv7 translation, not physical Thor or Android 13–16 certification.

Publication of these exact tested bytes is authorized. See
[object-action runtime receipt](docs/OBJECT_ACTIONS_RUNTIME_ACCEPTANCE.md).
Future APK changes require fresh evidence for affected behavior. Never replace
actual game progression with phase/memory/save writes or host fixtures.
Preserve the context-menu anchored hit rectangle, DLC/cache cleanup ownership,
and guarded serialized audio lifecycle. No generic NULL-callee skip is applied.

# Historical 0.1.10 delivery gate — passed

The user required autonomous correction of hidden UI and progression beyond
character creation before another APK. That requirement is satisfied for SHA256
45335ca99a15e2b26dcbaeb0547cb2edc184eb7fa302446abae22dd455fb40fb.
Actual Android execution verified visible UI, female customization, five traits,
name Alex, SceneGame/house/HUD, Save & Quit, a new-process saved-Sim load and live
interaction. See docs/RUNTIME_ACCEPTANCE.md and its evidence index/screenshots.

Run 41177712451 remains red only because a redundant final OCR step timed out
after the required checkpoints. Root and two independent reviewers accepted
the actual screenshots/logs. Preserve that distinction; do not claim the whole
workflow passed. The test environment was API30 x86/ARMv7 translation, not a
physical Thor or an Android13–16 gameplay certification. The old female crash
was investigated without a generic NULL skip and did not recur in this path;
its invalid-object origin remains unproven.

Publication of these exact tested bytes is authorized. Future APK changes need
fresh evidence for affected behavior. Never substitute phase writes, static
checks or headless sprite fixtures for required actual gameplay acceptance.
Source checkpoints and release publication are within the existing authorization.

# Build and preservation

Use isolated `--build-dir` and `--dist-dir` paths for internal builds. The local
builder verifies the package ID, version and launcher before accepting an APK.
Keep the application ID, signing key and private data location for install-over
updates. Signing files and complete user reports must remain outside Git.

The original assets are restored after the unsuccessful 0.1.9 index experiment.
The current UI fix changes only the guarded projection Z-scale instruction;
XY scaling and touch coordinates remain intact. Preserve the working RAM,
native-stack, code-flush and PVRTC corrections. ARM32 and 4 KiB page constraints
remain; do not advertise a universal ARM64 port.
