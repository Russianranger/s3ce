# Thor HUD hit testing — 0.1.12

The supplied physical-device report identifies S3CE0.1.11, ARM32, Android13,
AYNThor, normal rendering selected. The screenshot is1920×1080. The user
confirms object actions and saved-game continuation work. Three circled HUD
areas still reject or misroute taps, separate from the0.1.11 context-menu fix.

## Circled controls

These positions and dispatch outcomes derive from original ARM execution at
scale3.375. Corrected Thor actions remain a physical-device acceptance gate.

| Control | Intended action | Visible position / original defect |
| --- | --- | --- |
| Upper-left panel with green/red status dots | Expand/collapse Sim status-effect names (`Scene+21c`) | FrameX≈−23.8..128.1,Y168.8..492.8. Hit accepts rawX0..45 although the45-unit frame is drawn scaled; visibleX81/122,Y236 fail. |
| Chair above lower-left ellipsis | Buy mode (`SceneGame` mode13) | Tap center110,783. Earlier Pause test steals it because radius24 becomes81 before comparing with logical touch coordinates. |
| Lower-right wishes strip and plumbob | Wishes/Sim-information panel (`ffcec`, action3) | Strip1448,999 passes its raw rectangle but final decision compares logicalX against raw edges. Plumbob1804,965 works, but its inflated radius steals neighboring taps. |

Pause center113,965 and adjacent status/needs strip506,999 (action4) are regression
controls. Upper-left clipping is intentional: `fea4c` centers the45-unit panel at
`anchorX(45/2−6,2)`; the green dot is35.3,246.4. Rendering is unchanged. It is a
status-effects panel, separate from the top-edge action queue.

## Source evidence and correction

Pinned original APK SHA256:
`d42d0bf4a663abc3b1bb2abd0b350d93b6a2fa687a3b902f111a40c38a94f0d0`.
Unpacked S3E SHA256:
`8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a`.
Existing REA bridge provenance remains in ANALYSIS.md. No ready native REA
provider was available. Current REA instructions and existing analysis were
reused; focused fallback analysis used Capstone and Unicorn.

`SceneGame`107254 keeps raw touch inr7/r8, then converts stack copies through
Displayae4f0. Circle tests use those logical copies. Three `BLDisplay.scale(24)`
instructions at1073cc,107500,1075e0 become `MOVr0,#24`. Original anchors, circle
math, enable flags and route order remain. This removes false Pause-over-Buy and
plumbob-over-Wishes overlaps. At1077e0, `LDRr0,[sp,#24]` becomes `MOVr0,r7`,
keeping the final strip decision in the raw units already used by its rectangles.

The upper-left panel uses original metric readers925c4/92618 and width130a60.
Original atlas frame172/173/174 widths18+1+26 give45; height48 is doubled for the
mirrored frame. Its logical width45 was compared directly with rawX. The guarded
107844..10784c gateway calls the same width producer, then Displayae348(width),
and resumes the original rectangle call at107850. At3.375 its raw width becomes
151 by original truncation. The inherited six-logical-unit side margin and
canonical scale1 behavior remain. Expansion and status content remain original.

The Thumb gateway derives game base from guarded ARM return10784c, saves24 bytes
for8-byte stack alignment, restores overwritten width/height stack arguments,
skips the literal and returns to original ARM. It uses no JNI, allocation or
retained engine pointer. Seven source words change: four corrections and a
three-word gateway. Eleven exact instruction spans guard changed regions,
conversion/hit helpers, width producer and scaling helper. All validate before
any write; unknown/mixed generations fail closed; exact repeats are idempotent.
The tracked allocation lock and existing full instruction-cache flush still
order mutation. Global XY, depth correction, context menu, camera, saves and
shutdown behavior are untouched.

## Validation boundary

`emulate_hud_input.py` executes compiled production patch/gateway with original
ARM transforms, source metric readers, status width, circle/rectangle tests and
route selection. Twenty cases cover five dimensions/scales, low/high split game
mappings and two native helper locations. There are180 before/after dispatch
checks: Pause, Buy, plumbob, needs/status, Wishes, two visible status-panel
points, an outside-panel point and a world gap. Old high-resolution cases
reproduce Buy→Pause, swallowed Wishes and rejected visible panel taps; corrected
cases route correctly. Scale1 is identical. SP/canaries,r4-r11,d8-d15 survive.
Font width, animation interpolation, status membership, sound/click effects and
final panel/game-mode endpoints are fixtures; this is not Android gameplay proof.

`hud_input_test.c` checks exact changed words, every guarded byte, invalid spans,
helpers, partial generations, changed already-patched helper/literal and repeat
application. `verify_legacy.py` checks guard arrays against the pinned original
APK. Android/emulator and Thor evidence belong separately in the release/runtime
handoff. Green host tests alone do not establish device acceptance.
