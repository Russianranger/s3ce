S3CE 0.1.14 — Galaxy Z Flip3 landscape test

Created on the flip3 branch from the user-confirmed working 0.1.13 build. The game
now fits a centered 16:9 surface inside the available landscape content. On a
2640×1080 content area it uses 1920×1080 with 360-pixel side margins, preserving
proportions. Android safe insets are consumed once; the rendered surface and
view-local touches use the same dimensions. Side margins are inactive.

Normal landscape and reverse landscape are supported. Gesture ownership is
cancelled cleanly on margin exit, window/lifecycle changes and pointer removal.
The prior camera-radius/jewel repair and every native/render/action/save/audio
fix remain. This release adds no new startup-memory correction.

Actual full-game testing used an Android 11/API 30 Google APIs x86 emulator with
ARMv7 translation, KVM/SwiftShader and a 2640×1080 display. The real game child is
1920×1080 at [360,0,2280,1080]. Four process-cold menus across two final-APK runs
passed with zero startup failures, plus two separate normal saved-game restarts.
The completed run verifies character creation, save/load, visible Chair Sit,
Wishes with camera off/on, zoom, camera pan/release, status expansion/collapse,
Build chooser, walking, visible Home return, post-action save and normal Quit.
The final34-command run is green; earlier failed attempts remain in the receipt.

Android 15/API 35 executes the exact candidate Java helper DEX in a separate
SurfaceView fixture. Actual reverse-landscape rotation3, child-local center
DOWN/UP and visible rotation1 return pass in the same process, along with inert
margins, cancellation, sparse pointers, Home return and a nonzero stock cutout.
The API 30 game emulator could not supply a reverse-orientation sensor reading;
full-game reverse landscape remains a phone test. Live developer-forced resize
and removal of the optional cutout overlay retain narrower documented limits.

[Runtime receipt](https://github.com/Russianranger/s3ce/blob/flip3/docs/FLIP3_RUNTIME_ACCEPTANCE.md).
689 viewport host assertions, 24 assembled orientation paths,366-method DEX
analysis, 58 harness tests and original-ARM dimension/input checks also pass.

The Android 15 framework test executes the exact candidate Java helper in a
separate SurfaceView fixture. Its 64-bit-only emulator rejects the ARM32 game;
this does not certify the original engine on Samsung Android 15. The phone must
support 32-bit ARM apps and 4096-byte pages. The unfolded main screen is the target;
cover-screen/flex-mode gameplay has not been validated.

Install the APK over an existing S3CE installation without uninstalling or
clearing data. The application ID, key and private save location are unchanged.
Keep Original rendering (diagnostic mode) unchecked. A new phone needs its own
local save or a separately transferred save; installing an APK does not transfer
saves between devices.

Short phone test:
1. Fully unfold the Flip3. Launch in landscape and check both landscape directions.
2. Load an existing local save, or create normally. Tap status, Buy/menu, the
   bottom-right jewel with camera off/on, and nearby objects at their visible centers.
3. Pan and release, zoom, walk, and visibly complete an object action. Check
   side margins do nothing and drags do not remain held after leaving the game.
4. Press Home and return. Save and Quit, reopen/load, then try three process-cold
   starts without clearing data. Note every failure and any long black screen.
5. Home → app icon → Save report, then Share report file. Include Samsung
   model/firmware, installed 0.1.14/code 114, and screenshots of any mismatched tap.

APK: S3CE-0.1.14-flip3-arm32.apk / code 114 / 76,770,649 bytes.
SHA256: ea11252f93bdfbf2a9bb5b8a389e524d1dfb342c0eb8cc3f2e2115236634d19b
Production source: 2f3aba9f15313deb61f4f1769565da9d77f0f46c
