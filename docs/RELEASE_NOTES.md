S3CE 0.1.13 — camera touch area and bottom-right selection

Corrects the camera button intercepting taps on the bottom-right jewel and wishes
area. Its touch radius was scaled twice: about 398 pixels at 1920×1080 instead
of the original 118 pixels. One original-engine instruction now uses the correct
logical radius. Camera gestures, existing HUD/object-menu fixes and global XY
coordinates are preserved.

Actual Android testing used an Android 11/API 30 x86 emulator with ARMv7
translation, KVM/SwiftShader and a 1920×1080 viewport. The jewel opens the actual
Wishes panel with camera mode off and on; camera toggle, drag/release and zoom
work. Across two sessions, all four cold-menu starts passed with zero failures,
plus two saved-game restarts. The follow-up completed visible Bed Sit, post-action
save and clean native Quit. Both complete logs have zero fatal/ANR or late-audio
warnings. The first session remains failed on its 24-command harness limit;
its pending final save and missing Quit are retained. The follow-up is green.
[Runtime receipt](https://github.com/Russianranger/s3ce/blob/main/docs/CAMERA_INPUT_RUNTIME_ACCEPTANCE.md).

Host validation passed all 15 native sanitizer suites, 20 original-ARM layout
cases, 800 camera/HUD comparisons, 480 boundary/phase/fallback checks, 180 earlier
HUD comparisons and 24 harness tests. Previous fixtures left the camera region
disabled; the expanded regression reproduces the interception before checking
the correction. Original Java DEX and game assets remain unchanged.

This release retains the prior startup memory/diagnostic changes. It adds no
new startup fix and does not establish Thor LOW_MEMORY reliability. Physical
Thor camera/jewel confirmation, prior-save install-over and new Home/return
remain the next test.

Install over your existing S3CE app without uninstalling or clearing data.
Same ARM32 package, signing identity and save location. Keep Original rendering
(diagnostic mode) unchecked.

Short test using your existing save:
1. Tap the bottom-right jewel before and after toggling the camera icon. It
   should open its normal panel without switching camera mode.
2. Enable camera mode, drag the world and release. Check movement stops, then
   select the jewel again. Check zoom and one completed object action.
3. Save and reload normally. Try three process-cold starts, retaining your data.
4. Export Home → app icon → Save report, then Share report file. If a tap remains
   intercepted, attach a screenshot showing the tapped location. After a startup
   failure, export after reopening so retained previous-session evidence is included.

APK: S3CE-0.1.13-camera-input-arm32.apk / version code 113 / 76,770,649 bytes.
SHA256: ce8c54bffe5deeb00e6c81b3d942bfdd5f5480b63ef281d33b053cc255eb3a5e
Production source: b76f771113032361de079ee360588e0990426c08
Follow-up harness source: 537f768540eb962a6e9422a02ec4838c6b00249d
