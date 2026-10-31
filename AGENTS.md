# Current delivery gate

The user requires autonomous correction of the hidden UI and the crash observed
during female Sim customization. Do not present or publish another APK until a
full Android run shows visible UI controls and progresses through character
creation into gameplay. Isolated phase writes, static checks, ARM instruction
fixtures and headless sprite rendering alone do not satisfy this gate.

Record the tested APK hash, Android environment, screenshots and progression
evidence. Exercise female customization and investigate the reported native
crash; do not substitute a blanket null-pointer skip. Check gameplay and
save/resume after creation. State any emulator-versus-Thor limitations precisely.

Source checkpoints may be pushed to main within the existing authorization.
Keep release staging and APK publication unchanged until acceptance passes.
If a real runtime is blocked, keep the gate pending and report the blocker
honestly instead of sending another diagnostic APK for the user to test.

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
