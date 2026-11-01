S3CE 0.1.15 — Flip3 social-event crash test

The new Flip3 diagnostic report captures a native crash while copying a 1 MiB
image into a null allocation. The kiss event is the only event image with that
pixel size, strongly matching the reported Hot Smooch failure. This patch uses
the pixel bytes already owned by the image loader instead of allocating a
second copy. Other event artwork uses the same corrected path, including
marriage, WooHoo, hiring/promotion and skill milestones; those additional crashes
were not observed in the report. See docs/SOCIAL_IMAGES.md for evidence/limits.

Two separate restored-activity Java failures also appear in the report. Restored
Main now completes the same guarded native bootstrap as the normal launcher
before creating the engine thread. Failure retains diagnostics. No automatic
restart hides a failed start.

The user confirms good UI on the physical SM-F711U1 running Android 15. This
release keeps the accepted centered 16:9 landscape viewport and all existing
camera, jewel, object-action, graphics, audio and save fixes. No original assets,
heap budget, relationships or saves are changed. Fully local ARM32 gameplay,
4 KiB pages, min SDK 26 and target SDK 28 remain required.

Validation: all 107 original immutable images have identical decoded pixels and
mipmaps after the ownership change; 12 compiled ARM cases cover ownership and
cleanup. Sixteen native host suites, 64 startup assertions, 689 viewport host
assertions, exact candidate assembled DEX checks and 379-method static analysis
pass. Actual API30 ARMv7-translated gameplay passes two normal cold starts, separate
Boot-bypassing Main entry, creation/save/new-process load, Chair Sit, Home return,
zoom/pan/release, jewel in both camera modes, walking, post-action save and normal
Quit. Zero fatal/ANR; all24 UI commands retained. Android15 exact-helper tests
support eight core input/rotation checks; both whole runs remain red on documented
size-compat/cutout simulation limits. Hot Smooch with the user's save remains a
phone regression test.

Install this APK over your existing S3CE app. Do not uninstall or clear data.
Keep Original rendering (diagnostic mode) unchecked. The same application ID,
signing certificate and private save location preserve install-over updates.

Short phone test:
1. Load your existing save and repeat Hot Smooch. Let the animation and any event
   picture finish. Repeat a few times if normal gameplay permits.
2. Try another available social action. If already available in this save, try
   WooHoo or marriage; do not change relationships just to reach them.
3. Check the bottom-right jewel, camera pan/zoom, walking and an object action.
   Save and Quit, reopen and load. Press Home and return once during gameplay.
4. After saving, close the game and try three process-cold starts. Record every
   failure; successful retries do not erase earlier failures.
5. Home → S3CE app icon → Save report, then Share report file. Export immediately
   after a crash/retry. Include the interaction, visible result and approximate
   crash time; report should identify 0.1.15-flip3-socials / code 115.

APK: S3CE-0.1.15-flip3-socials-arm32.apk / code 115 / 76,774,745 bytes.
SHA256: a759fb156efb526149e3c0e3a9ca3bba4d5646aff4198ae8946dbc7947c7f5eb
Production source: e2eac7e24c712ba77469794d9c802422e5e25bdc
