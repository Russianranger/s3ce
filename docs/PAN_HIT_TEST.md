# Camera button hit testing

After installing0.1.12, the user reports that the other controls work on the
Thor, but the bottom-right plumbob remains inaccessible because tapping that
region activates camera pan mode. This new observation supersedes treating
all remaining lower-right misses as tutorial gating.

## Confirmed source defect and minimal correction

Original `SceneGame::107254` tests the camera button first, before Pause, Buy,
plumbob and the lower strips. It converts raw coordinates to logical UI space
at107284. At107288 it then reads `Scene+264`, which both initialization105f88
and every camera render112f90 compute as `Display.scale(35)`. Its sole camera
hit consumer compares this already scaled radius with logical touch coordinates.
Converting that logical hit boundary back to physical screen coordinates
introduces a second scale factor; no visible circle is drawn for this boundary.

At1920×1080, scale3.375, original rendering and source soft-float math give:

| Quantity | Original/source-derived value |
| --- | --- |
| Camera logical center (`Scene+25c/+260`) |1175,615 |
| Camera physical center |1685.625,793.125 |
| Stored radius (`Scene+264`) |118 after original integer truncation |
| Incorrect physical hit radius |398.25px |
| Correct logical radius / physical radius |35 /118.125px |
| Plumbob sample / distance from camera |1804,965 /≈209px |

Thus the old circle consumes a plumbob tap before its corrected0.1.12 handler
runs. It also consumes the Wishes strip. This is a different earlier precedence
failure from the already corrected24-unit plumbob/Pause/Buy bounds.

Only game instruction107288 changes: `LDRr0,[r4,#0x264]` (`e5940264`) becomes
`MOVr0,#35` (`e3a00023`). Existing per-frame rendering, original coordinates,
enable/toggle flags, the35-unit policy, the75% fallback and all0.1.12 repairs
remain. The fallback computes26 logical units through the original soft-float
path. The initializer/render producers are deliberately unchanged because their
field is recomputed every frame and the correction belongs to its input consumer.

The original render tail112f4c..112ff0 recomputes center/radius and chooses the
on/off image through `Scene+26a`; both source images are64×64, with a36×36 alpha
bounding box. Their opaque drawing is121.5×121.5 physical pixels at this scale.
The full216×216 transparent quad and inherited118.125px hit radius are preserved.
No global touch offset or neighboring hit-area enlargement is applied.

## Camera mode and click precedence

A normal camera hit is accepted in phases6,21 or7 when `Scene+a40&0x2000` is set.
However, the real click dispatcher104014 calls107254 a second time withforce1
if the first pass declines. This fallback bypasses the flag and uses75% radius.
Tests must exercise that path too; merely clearing0x2000 does not disable it.

`Scene+26a` selects the mode image and real camera gestures. Existing drag routing
10fbac→10b160 and1102c4..1102d0 are unchanged, as is the separate controller toggle
at11024c. The same corrected hit circle applies when mode is on or off.

## Evidence and checks

Pinned original APK SHA256:
`d42d0bf4a663abc3b1bb2abd0b350d93b6a2fa687a3b902f111a40c38a94f0d0`.
Unpacked S3E SHA256:
`8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a`.
Existing REA analysis/provenance remains in ANALYSIS.md. The native provider was
unavailable; focused Capstone and Unicorn fallback analysis reused the existing
pinned binary and assets. Reports and private inputs remain outside Git.

The previous HUD fixture left `Scene+264=0` and camera flag0x2000 clear. It did
not exercise real rendering or early camera precedence. Expanded tests now
execute the exact original camera render tail, both original click-dispatch
passes, original transforms, circle tests and mode-byte toggle. The0.1.12
counterexample retains all seven previous HUD instruction repairs; only its
original107288 load is present. Old plumbob/Wishes taps toggle the camera;
corrected taps reach their panel endpoint in both camera modes.

Twenty layout/helper cases cover five dimensions/scales, low/high split game
mappings and two native helper locations. They retain180 previous HUD dispatch
comparisons, add800 old/new camera-HUD comparisons, and480 camera phase/flag/
fallback/boundary checks. They include camera mode on/off, flags clear/set,
phases6/21/7, the real second fallback pass and a nearby world point after both
passes decline. Canonical scale1 old/new results agree. Samples around radius
boundaries allow two logical units for the original raw-pixel/soft-float integer
quantization. SP/canaries,r4-r11 andd8-d15 are checked.

Render virtual draw, font/status dependencies, panel/game-mode endpoints and
final world continuation are explicit fixture boundaries. Host selection does
not prove completed Android gameplay. Actual candidate Android/Thor checks must
record plumbob activation with camera enabled and mode on/off, normal camera
gestures, object actions, save/reload and clean exit separately.

The patch still validates every instruction span before any write. Three new
spans guard the camera hit, initializer and per-frame renderer; fourteen spans
and all eight changed words are checked for tampering, partial generations,
invalid addresses, unchanged surroundings and idempotence. The existing tracked
allocation lock and full instruction-cache flush preserve ordering.

## Read-only runtime attribution

The existing guarded pointer observer also records SceneGame phase1c0, HUD
flagsa40, camera center25c/260, stored radius264 and mode byte26a. The render's
stored radius remains scaled; the corrected input uses its original logical
constant. These diagnostic reads use the existing validated memory-copy path,
never dereference runtime pointers directly, and write no engine state. Menu
and Game fields remain separated by the exact vtable/profile checks. Tests
cover every failed read, both class exclusions, largest values and512-byte
output capacity. Snapshots occur after callback enqueue, before a later frame
consumes input; use subsequent frames/actions for resulting state evidence.
The live-frame metadata exposes the same raw observer text for review.

The signed candidate's original bridge and launcher DEX are byte-identical to
0.1.12; only native code, version manifest and signing records differ. All15
native sanitizer suites, the original22 runtime harness tests and byte-exact
reconstruction pass. The harness-only continuation adds two tests for its
40-command bound and coupled frame uploads; all24 tests pass. Android evidence
and its original failed-session limits are recorded in
[CAMERA_INPUT_RUNTIME_ACCEPTANCE.md](CAMERA_INPUT_RUNTIME_ACCEPTANCE.md).

The previous 0.1.12 Go to Town screenshot demonstrated a hint path, not a
captured phase21 value. The ordinary prefix had already selected No at the
optional tutorial prompt. Do not infer phase/flags from that hint alone or
attribute every old strip miss to gating. Enabled camera precedence is now
independently reproduced; use actual mode/panel frames plus sampled state/time
for the new runtime. Observer logging is sampled, so the latest retained line
may precede the latest command; check callback number/time before attribution.
