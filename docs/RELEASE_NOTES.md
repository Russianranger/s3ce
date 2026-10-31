S3CE 0.1.12 — HUD taps and retained startup diagnostics

Corrects the circled HUD controls: upper-left status panel, chair/Buy button,
and lower-right wishes strip. Preserves original drawing and object actions.
Pause, needs/status and plumbob are included in nearby-control regression checks.

Android records the latest unsuccessful Thor process as LOW_MEMORY. Removes
an unused GL-view CPU bitmap (4,147,200 pixel bytes at 1920×1080), and retains
startup phases, memory checkpoints and four previous processes' diagnostic logs.
Thor startup reliability still needs physical confirmation. The older native
SIGSEGV and historical emulator translation abort are separate records.

Host checks passed: original ARM HUD/context-menu tests, 15 native sanitizer
suites, assembled input/audio/surface/session DEX regressions, 348-method static
DEX analysis, retained-session persistence and signed APK reconstruction.
Android11/API30 x86/ARMv7-translation run passed: four process-cold menu starts,
zero failures, normal female creation/save/restart/load, visible status/Build
controls, completed Bed Sit, another save and normal fatal-free Quit. Wishes
activation remained unconfirmed during original tutorial gating; check it on
your existing save. New Home/return and physical Thor memory reliability remain
untested. The emulator save was created by this candidate, not imported from0.1.11.
Full evidence: docs/HUD_STARTUP_RUNTIME_ACCEPTANCE.md.

Install over existing S3CE without uninstalling or clearing data. Same app ID,
certificate and save location. Keep Original rendering unchecked. Requires
ARM32 support and 4 KiB pages; target SDK 28 remains intentional.

Short Thor test:
1. Load your existing save. Tap the left status panel near its visible right
   edge, then the chair/Buy button; return to gameplay.
2. Tap the wishes strip/plumbob. Check nearby Pause and needs/status.
3. Complete an object interaction, walk, pan and zoom. Save/quit, then reload.
4. Fully close/force-stop without clearing data and start again three times.
   Note every success/failure; a retry is a separate attempt.
5. Export after any failure before retrying when possible, and after the retry:
   Home → app icon → Save report. Attach it and any still-offset screenshot.

APK: S3CE-0.1.12-hud-startup-arm32.apk / code 112 / 76,770,649 bytes.
SHA256: b73c15341acbb61e7fa85173eb440650c665a65df57ce1ac46caf0e2d7325b64
Candidate source: 6b6ebe2272864839e19b4ba15b216bcfc6979877
