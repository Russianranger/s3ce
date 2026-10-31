S3CE 0.1.11 — object actions and clean shutdown

Fixes visible object-action buttons rejecting taps. The original menu drew its
rows using Display anchoring while its coarse touch rectangle stayed at Y=0; the
correction aligns that boundary with the original visible layout. Rendering,
camera gestures, global touch scaling and action dispatch are preserved.

Also corrects two shutdown ownership races: DLC images now release before their
renderer cache, and queued audio callbacks cannot use a retired AudioTrack after
native shutdown. Current-track audio playback remains active.

The exact APK completed an actual Android run through female creation, five
traits/name Alex, house gameplay, save/restart/load, a visible Chair Sit followed
by a seated Sim, another save, and clean normal Quit back to the launcher. The
accepted run contains no fatal crash/ANR or late-audio warning. Chair Sit was
directly exercised; Sofa and C3 Android Home/resume were not. Source proof and
all failure history are in docs/OBJECT_ACTIONS_RUNTIME_ACCEPTANCE.md.

Validation used Android 11/API 30 x86 with ARMv7 translation, Emulator 31.1.4/KVM/
SwiftShader, 1920×1080 and 4 KiB pages. A first same-byte attempt aborted inside the
emulator translator; the retry completed. No new physical Thor or Android 13–16
certification is claimed.

Install over your existing S3CE app without uninstalling or clearing data. Keep
**Original rendering (diagnostic mode) unchecked**. Same package/signing key/data
location preserve update compatibility. Reports: **Home→app icon→Save report**.
Requires 32-bit ARM app support and 4 KiB pages; target SDK 28 remains intentional.

APK SHA256:
3f7698294ace0e7a78bb32524811ae237701395dc87184102cdc4c47534d07f5
