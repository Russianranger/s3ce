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

## Runtime delivery gate

Internal C2 APK SHA256
`a5a98513afa16520bc86b2aff67fda2b68d3505755d57e69e75cd6499453aa48`,
76,762,457 bytes. Native SHA256
`d0f375b7e74b8174f0f00472a3b3eb6f44f0b5d2f48ffcfa1f03e812b236cf68`.
Run [41212609908](https://github.com/Russianranger/s3ce/actions/runs/41212609908),
source `c49b2cdf62ee73b15a3dab3b90b79af40689e4a6`, completed the female creation,
house gameplay, normal save and new-process load prefix. Ordinary frame-guided
Android input then selected the visible Cheap Dining Chair **Sit** action at
1235,353. Frame6 shows the standing Sim, empty chair and action menu; frame7
shows the Sim seated at the table with the chair action icon. Root and two
independent reviewers inspected the hash-verified raw frames. Frame7 PNG SHA256:
`5aa234152451b1e36157433a166bcc4f9eaea0e11b4767e4c8379d5d886c3655`.
This is actual Chair Sit execution through the shared context menu; Sofa itself
was not exercised. No game-memory or save-file values were written.

Normal Save and Quit returned to the main menu. Native Quit returned from Main
and requested Activity.finish, but a queued audio callback then caused a genuine
Java fatal exception. The workflow correctly failed and C2 is **not accepted
for release**. Artifact13047588702 is112,228,778 bytes, ZIP SHA256
`e690ad48715216e3af370d33f4a0cb429c937c5016281fb1d2fa704b3bee24ab`.
The follow-up C3 audio lifecycle correction must repeat actual interaction and
clean Quit before publication; `.validation` is internal staging only.

Do not publish a new APK based only on menu dismissal or the host ARM fixtures.
The runtime environment is Android11/API30 with ARMv7 translation; physical Thor
Android13 behavior for the new patch still needs to be distinguished precisely.

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
The separate Java failure below still blocks clean-Quit acceptance.

## Queued audio callback after Quit

C2 run41212609908 stopped sound at15:27:49.402, returned from native Main at
15:27:49.440 and requested Activity.finish at15:27:49.441. At15:27:49.480, an
already-queued AudioTrack position callback called generateAudio after native
shutdown, then dereferenced the now-null track in
`SoundPlayer.onPeriodicNotification` at15:27:49.481. The original stop already
detaches the listener, which does not cancel callbacks already queued by its
delegate. A targeted audio lifecycle correction is in progress; it must reject
retired-track callbacks before JNI and coordinate an in-flight callback with
stop/restart while preserving normal playback.
