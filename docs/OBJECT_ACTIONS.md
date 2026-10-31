# Object-action selection — 0.1.11

The 0.1.10 Thor report confirms visible UI, character creation into the house,
walking, saving and camera zoom/pan. Selecting an object opens its action menu,
but tapping a visible action does not select it. This is a separate acceptance
gate from the completed 0.1.10 creation/save flow.

## Confirmed coordinate mismatch

Original UIContextMenu render function `0x857ac` uses Display's anchored layout.
SceneGame transforms touch points into that same coordinate system. However,
its final bounds setter at `0x86334` supplies a fixed Y=0 and height=320. The
original coarse hit test `0x11fb8c` rejects touches before row selection runs.
At 1920×1080 and scale3.375, the visible logical Y interval is380..700, so every
visible action fails that initial0..320 boundary.

Full original ARM render execution produces these sofa label centers, matching
the user's actual screenshot:

| Action | Logical center | Physical center at1920×1080 |
| --- | --- | --- |
| Sit |1010,420 |1128.75,135 |
| Relax |1041,485 |1233.375,354.375 |
| Have a nap |1041,550 |1233.375,573.75 |
| Walk to |1010,615 |1128.75,793.125 |

The original rectangle is `[930,0,200,320]`. The corrected rectangle is
`[930,380,200,320]`; its Y comes from the exact original
`Display::anchorY(display,0,2)` at `0xae458`. No row geometry, drawing, global
input transform, action ID or world interaction is replaced.

## Production correction and checks

`native/context_menu.c` replaces only the ten-instruction bounds tail at
`0x86310..0x86334`. A position-independent ARM thunk passes the original menu
and game allocation base to the Thumb helper, then resumes the original
`0x86338` stack/register epilogue. The helper executes the original soft-float
X-to-int conversion, Display Y transform and `0x81bc4` rectangle setter with the
unchanged X, width200 and height320. It allocates no heap, calls no JNI, and
retains no game pointer between calls.

Six instruction fingerprints guard the render entry/tail/epilogue and all
three reached helpers. The patch runs under the tracked code-allocation lock
before the existing full allocation instruction-cache flush. Unknown code,
short/wrong/overflowing spans, invalid helper addresses, tampering and changed
already-patched literals are refused; repeated exact application is idempotent.

Fourteen native ASan/UBSan suites pass, including the separate shutdown-order
guards. The exact compiled production C helper
and patch execute with the original ARM render, bounds, selection, timer and
SceneGame action-ID extraction in `native/tests/emulate_context_menu.py`.
Twenty combinations cover two native helper addresses, low/high split game
addresses and five dimensions/scales, including canonical portrait dimensions.
They check160 original/corrected row results,100 outside/cancel cases,60
inherited gaps,100 raw/logical input-transform checks, original drawing inputs,
stack/canaries, r4-r11 and d8-d15.
Legacy480×320/scale1 behavior is unchanged. Host fixtures model graphics/font,
allocation, sound, selection visuals and the final world-action boundary; they
do not establish completion of a real interaction on Android.

The isolated APK passes original-asset/configuration preservation, source and
native-hardening checks, v2/v3 signature/package/version/launcher checks,
assembled touch/lifecycle/GL regressions and310-method DEX analysis with no
static type/register failures.

## Runtime delivery gate — passed for C3

Accepted exact C3 APK SHA256
`3f7698294ace0e7a78bb32524811ae237701395dc87184102cdc4c47534d07f5`,76,762,457 bytes.
[Run 41215805134 attempt 2](https://github.com/Russianranger/s3ce/actions/runs/41215805134/attempts/2),
source `02b1375300f541f3d092b3d1720d16031f4b7a06`, completed female creation,
house gameplay, normal save and new-process load. Ordinary bound Android input
selected the visible Cheap Dining Chair / Sit action at 1235,353. Frames 7/8/10
show the menu, approach/queue, then seated Sim. Normal post-action SaveQuit and
main-menu Quit returned from native Main and finished the Activity into Compat.
The full accepted log has zero fatal/ANR matches and no late-audio warning.

Root and two independent reviewers accepted those actual raw frames and full
artifact13048233710, ZIP SHA256
`95448d02d49e77fd5a3175e000673f6227411e163436492bdeaf5d0e097f3c8a`.
The original automated gate_passed=false awaiting visual review remains intact;
manual signoff is separately recorded in the [durable receipt](OBJECT_ACTIONS_RUNTIME_ACCEPTANCE.md).
No game memory, phases or save values were written. Sofa itself and C3 Android
Home/resume were not directly exercised. Runtime was API 30 x86/ARMv7 translation,
not new physical Thor/Android 13–16 acceptance.

C2 had already completed Chair Sit but was rejected on its late audio Quit NPE.
C3 attempt 1 aborted in the emulator ARM translator's VADDL alignment check before
UI; its exact origin remains unproven. Identical C3 bytes passed attempt 2. Both
failures remain in the receipt/index. Publication uses only accepted C3 bytes.

## Separate exit crash

The current report also records a later null indirect call at game`0xb0d38`,
inside `midp::ImageIPhone` destruction after loading/menu audio transitions.
It is temporally separate from the earlier sofa action taps. Original ARM ownership execution reproduces the lifetime violation: the DLC
manager releases a cached image after CacheGLES was destroyed. The guarded
shutdown correction preserves Display destruction at its original point and
defers only CacheGLES deletion until after the existing DLC cleanup. No manager
is released early, and no indirect call is suppressed. Sixteen compiled-production cases execute the original main cleanup, including
both GLES cache types and CPU/GPU-backed images, at low/high split game and
native addresses. Old GPU-backed cases reproduce the freed-cache access; the
repair releases the image/GPU resource and each owner once, preserving other
cleanup order, SP/LR, r4-r11 and d8-d15. Filesystem lookup, uploaded texture
handles, GPU deletion and unrelated subsystem termination are fixture inputs or
modeled boundaries. This identifies an original lifetime hazard consistent with
the report; the report did not capture its precise cached DLC entry. Actual
Android C2 execution reached native Main return without a native fatal signal.
The separate Java failure below blocked C2; corrected C3 passed clean Quit.

## Queued audio callback after Quit

C2 run41212609908 stopped sound at15:27:49.402, returned from native Main at
15:27:49.440 and requested Activity.finish at15:27:49.441. At15:27:49.480, an
already-queued AudioTrack position callback called generateAudio after native
shutdown, then dereferenced the now-null track in
`SoundPlayer.onPeriodicNotification` at15:27:49.481. The original stop already
detaches the listener, which does not cancel callbacks already queued by its
delegate. C3 replaces six guarded SoundPlayer methods. A shared explicit monitor serializes
callback generation/write with stop, start, pause, resume and volume. A callback
must name the current playing track before native generation and again before
write; stop retires that track before detaching its listener and releasing it.
Exception handlers release the monitor and rethrow the same exception. Original
initialization, sample format/rate/buffer sizing and native generation remain.

The actual assembled C3 DEX passes normal lifecycle, 1,000 delayed callbacks,
stop/restart identity, concurrent generation/write drain, reentrant retirement,
and exception/monitor checks. The old C2 DEX reproduces the observed delayed
generation and null-track write. Six original method fingerprints plus native
generation/init guards reject tampering before any write; repeat application is
idempotent. All 310 implemented C3 DEX methods pass static register/type analysis.
These host checks model Android AudioTrack and native mixing boundaries, so the
actual C3 Android interaction/clean-Quit replay above supplies the required evidence. C3 APK SHA256
is `3f7698294ace0e7a78bb32524811ae237701395dc87184102cdc4c47534d07f5`;
only classes.dex and signing records differ from C2. Native bytes, the launcher
DEX, AndroidManifest and original assets remain identical.
