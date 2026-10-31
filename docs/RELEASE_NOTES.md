S3CE 0.1.10 — visible UI and verified character creation

Restores the missing character-creation panels, tabs, icons and buttons. A guarded
native correction prevents high-resolution scaling from clipping UI projection
depth; XY rendering and touch coordinates stay unchanged. Original game assets
are restored after the unsuccessful 0.1.9 indexed-quad experiment.

The exact APK completed an actual Android run with female gender, three hairstyle
changes, five traits, name Alex, confirmation into the house with full HUD, Save &
Quit, a full process restart and loading the saved female Sim with responsive
input. No fatal crash or ANR appeared in the captured run. The previous female
crash did not recur in that path; its original invalid-object cause is unresolved.

Validation used Android 11/API 30 Google APIs x86 with ARMv7 translation,
Emulator 31.1.4/KVM/SwiftShader, 1920×1080 and 4 KiB pages. This is not physical
Thor or Android 13–16 gameplay certification. The final automated run remains
red because a redundant final OCR step timed out after the required checkpoints;
those screenshots/logs passed manual review. Details: docs/RUNTIME_ACCEPTANCE.md.

Install over the existing S3CE app without uninstalling or clearing data. Leave
**Original rendering (diagnostic mode) unchecked** and start the game. Same package,
signing key and private-data location preserve update compatibility. The Report
overlay was removed because it covered an original control; use **Home → app icon
→ Save report** to access diagnostics.

Requires a device supporting 32-bit ARM applications and 4 KiB pages. ARM64-only
and 16 KiB-page devices remain unsupported. Android 13–16 are compatibility
targets, not four separately verified gameplay environments.

APK SHA256:
45335ca99a15e2b26dcbaeb0547cb2edc184eb7fa302446abae22dd455fb40fb
