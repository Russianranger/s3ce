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

Pending: select a real object action through ordinary Android input and retain
screenshots showing the Sim performing it. Verify continued UI and save/reload.
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
Android Quit verification remains a delivery gate.
