# Current work — object-action selection (0.1.11 pending)

The user physically verified 0.1.10 on the Thor: UI, character creation, house,
walking, saving, camera zoom and pan work. Visible object-action buttons do not
accept taps. Preserve those working behaviors. Do not present or publish a new
APK until normal Android UI input selects an object action and the Sim completes
it; retain actual screenshots, logs, exact APK hash and environment limitations.

Source analysis identifies UIContextMenu's coarse rectangle Y=0,H=320 while
visible anchored rows move into logical Y380..700 at1920x1080/scale3.375.
Correct only its rectangle origin using the original Display Y transform;
retain original rendering, input transforms, action selection and game logic.
Verify the compiled helper and ARM thunk, source fingerprints, all row/negative
cases and legacy dimensions before runtime acceptance. The current report also
contains a later ImageIPhone/render-cache teardown crash; distinguish it from
the earlier menu tap failure and avoid speculative NULL skips.

Internal C2 run41212609908 completed a real Chair Sit through the visible action
menu, but clean Quit correctly failed on a queued SoundPlayer callback after
native Main returned. C3 adds guarded, serialized audio lifecycle ownership and
retired-track rejection. Require a fresh real object action and fatal-free native
Quit on the exact C3 APK before publication; C2 remains unreleased.

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
