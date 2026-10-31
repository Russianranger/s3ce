# Current delivery gate — passed for the frozen 0.1.10 APK

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
