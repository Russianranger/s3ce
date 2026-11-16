S3CE 0.1.16 — romance from close friendships

Good Friend and Best Friend can now progress to Budding Romance through normal
successful romantic interactions. The two added tuning rules use the same 10-point
romance threshold as Friend. This applies to all NPCs, including Luke, Jake,
Jack, Walter and Ruth. Reaching a friendship stage does not automatically start
a romance; traits, conversation context, acceptance, existing partners/jealousy
and later relationship progression remain the original game rules.

Every old transition keeps its original priority. All 677 other resource payloads,
both Java DEX files and the native compatibility ELF are byte-identical to the
accepted 0.1.15 release. The Hot Smooch crash fix, centered 16:9 Flip3 landscape
viewport, accurate touch targets, object actions, camera, audio, cleanup and saves
are preserved. The save format, application ID and signing key are unchanged.
Fully local ARM32 gameplay still requires 32-bit ARM support / 4 KiB pages, min SDK 26
and target SDK 28. Original rendering (diagnostic mode) stays unchecked.

Host validation: six independent asset-integrity tests, 76 runtime-harness tests,
16 native sanitizer programs and 764 original ARM loader/resolver/setter runs pass.
The latter use the exact candidate resource and verify all 13 NPCs, all 15 states,
threshold boundaries, original priority and normal score reset/NPC isolation.
Their UI/goal/scene boundaries are modeled; they are not Android conversations.
Actual Android11/API30 ARMv7-translated gameplay passes two normal cold-menu
checks (zero failures), separate cold Main entry, normal creation/save/load,
Home return, completed Bed Sit, zoom/pan/release, jewel in both camera modes,
floor walking, post-action save/new-process reload, final save and normal Quit.
The full log has no fatal/ANR or matching game-process Java/audio errors.
Nine scoped Android15 viewport-helper checks pass; that64-bit-only image cannot
run the ARM32 game. The documented cutout-removal fixture limitation remains.
Actual Good/Best Friend romance progression and persistence remain the focused
phone test with your existing save. See docs/RELATIONSHIP_RUNTIME_ACCEPTANCE.md
for runtime evidence and limitations.

Install this APK over your existing S3CE app. Do not uninstall or clear data.

Short phone test:
1. Load your existing save. Choose a Sim already shown as Good Friend; use normal
   successful romantic interactions until Budding Romance appears. Ordinary
   rejection still applies. Take a screenshot of the status/notification.
2. Repeat with a Sim shown as Best Friend if available. Luke, Jake, Jack, Walter
   and Ruth use the same new rules; test whichever are already close friends.
3. Save and Quit, reopen and load; confirm the new romance status persists.
   Try another available romantic action, including Hot Smooch if offered.
4. Check walking, an object action, camera pan/zoom and bottom-right jewel. Save,
   press Home and return, then try three process-cold starts with data retained.
5. Home → S3CE app icon → Save report → Share report file. Include the Sim,
   relationship before/after, successful/rejected actions and any crash time.
   The report should identify 0.1.16-flip3-romance/code116.

APK: S3CE-0.1.16-flip3-romance-arm32.apk / code 116 / 76,774,745 bytes.
SHA256: f0258cf188b12208cbadaa97e0414feeab5b4fb1a2779bfc6a61452b22eaa6e2
Production source: 024355d3a6af9e6f45c2c0c663db284470444a32 (flip3).
