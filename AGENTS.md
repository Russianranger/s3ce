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
