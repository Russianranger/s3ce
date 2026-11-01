# 0.1.14 Flip3 runtime review — accepted test candidate

Exact signed APK: `S3CE-0.1.14-flip3-arm32.apk`, code 114,76,770,649 bytes.
SHA256 `ea11252f93bdfbf2a9bb5b8a389e524d1dfb342c0eb8cc3f2e2115236634d19b`.
Production source `2f3aba9f15313deb61f4f1769565da9d77f0f46c`; final harness
source `3d486a62bf9023be12e584a84d1d66aa68b8146c`. The helper DEX is
`61daef3156c105392db9046f9564c460379a374c20a3235d5f1391a35d272f30`.
Native source and all accepted0.1.13 compatibility fixes are preserved.

Root and independent reviewers accept these exact bytes as a focused Flip3
phone-test candidate. This is manual visual/archive acceptance. Original
`acceptance.json` remains `gate_passed=false`, awaiting visual review; it is not
rewritten to claim an automated gameplay gate. Publication uses the frozen
signed delta, with no rebuild or resign. Physical Samsung acceptance remains next.

## Completed full-game run

Green [run 41263509428](https://github.com/Russianranger/s3ce/actions/runs/41263509428),
attempt1, uses the exact APK above. Full artifact13068040004 is213,172,849 bytes,
ZIP SHA256 `916bcf81eb25ff2656dde8157315a85402eecaa46a9a0e2b5035c2e9603fb366`.
All 2,393 extracted members were verified. Raw acceptance SHA256 is
`17e9bf5856438b40dada0e503e1d92b0a36ed9fa0568a1c3e59e5c031ce7cd83`.

Environment: Android 11/API 30 Google APIs x86 revision16, ARMv7 translation,
Emulator 31.1.4/KVM/SwiftShader,3GiB guest RAM and4096-byte pages. Display 2640×1080;
actual native child[360,0,2280,1080],1920×1080. All progression is ordinary Android
input: no game phases, memory or save contents were edited.

| Evidence | Observed result |
| --- | --- |
| Cold menus | Both render correctly, PIDs4127/6451;0 failures. Across both exact-final-APK runs, four cold menus pass with0 failures. |
| Creation/save/load | Normal female creation/traits/Alex/house, normal SaveQuit, then new-process saved-Sim load6451→12489. Prefix save mtime1793499070→1793499354. |
| Home/return | SamePID12489, actual child unchanged. Early Home capture is black; the next visible capture5.87s later renders the Pause/house. Subsequent ordinary controls/actions work. This is bounded recovery, not an instant-return or physical timing claim. |
| Live1–3 | Pause closes; visible zoom slider changes scene magnification; timed New Wish closes at its visible X. |
| Live5/6/8 | Actual Cheap Dining Chair/Sit selection, then settled seated pose; still seated after closing Wishes. Completion uses supported pose, not menu disappearance. |
| Live7/14 | Actual Wishes panel opens with camera mode off and on. Camera mode comes from visible toggle/pan sequence, not stale observer text. |
| Live9/11–16 | Camera toggles, world pan changes angle, then static world crops remain pixel-identical across 37.12s after release; camera turns off. |
| Live20–25 | Buy introduction and actual chooser; floor tap moves Sim kitchen→front room; visible Well rested status expands and collapses. |
| Live28–31 | Pause, SaveQuit confirmation, loading, then actual complete main menu. Both normal save files advance02:15→02:41UTC (minute-precision listings),2562/90 bytes. |
| Live32/33 | Actual Quit dialog, then Compat114 with Original rendering unchecked; Native Main returns and Activity finish is requested. Command34 finish passes the unchanged native-Quit guard. |

Unsuccessful or interrupted attempts remain: live4 bed tap produced no menu/action;
live10 pan was interrupted by Go to Town; live17 status by New Wish; live19 has
no accepted expanded-label endpoint while the effect list was empty; live26
Pause was interrupted by Lonely. None is substituted for a successful endpoint.
No bed action is accepted. Sampled native observer298/410 remains stale across
later menus and exit; visible sequence, advancing saves and shutdown logs are
separate evidence.

The complete47,470,274-byte log SHA256 is
`a2d2612b2a7a576f7b5757054ac4748c2343d8b41f2bf023f7b4e2d7a42a77a7`.
It has0 fatal/ANR and0 late-audio exceptions. Audio stops, GL terminates, SoundPlayer
stops, Native Main returns 02:43:34.835UTC, finish is requested 34.837 and Main is
destroyed finishing=true 35.190. Retained idle package PID is expected; game Main
is absent and Compat resumes. Existing diagnostic GL query0x500 remains bounded
(23current,16/21previous); this is not a graphics-error-free claim.

## Current scope and next test

The API 30 game emulator does not rotate to reverse landscape, even with corrected
negative-X stimulus. Actual Main remainsrotation1. Captured Activity/DisplayRotation
records show SENSOR_LANDSCAPE6, enabled Goldfish accelerometer, filteredXYZ all0,
predicted rotation−1 and NaN tilt history despite commandOK. Its raw unavailable
case and strict visible rotation1 restoration are retained. Full-game reverse
landscape remains a phone test; no actual game3→1 sequence is claimed.

Separate green Android 15/API 35 run 41263509512 executes the exact helper DEX and
proves actual same-process rotation3, accurate center DOWN/UP and visible rotation1
return, plus cancellation/multitouch/margins/Home and enabled-cutout fitting.
The API 35 image rejects the ARM32 game because it has no32-bit ABI. It is framework
helper evidence, not original-engine gameplay or Samsung certification. See
FLIP3_ANDROID15.md for the one pre-probe launcherANR, live-resize/fresh-fixture
boundary and unproved stable restoration after removing the optional overlay.

Host checks pass689 viewport assertions, 24 assembled orientation paths,
366-method DEX analysis with0 failures,58 harness tests and10 original-ARM
Display/input dimension/mapping cases. These supplement actual Android execution.
The evidence index retains every older attempt and the separate manual decision.

Next: install the signed Flip3 release over an existing same-signed installation,
keep Original rendering unchecked, test unfolded landscape in both directions,
visible HUD/object actions, save/load, Home/return and three process-cold starts.
No prior physical-device save was available locally; no cross-device save transfer
is implied. Samsung ARM32/4096-byte-page/native-driver behavior needs that test.
Export Home→app icon→Save report and Share report file after testing or a retry.

# Historical implementation and validation attempts

## Corrected candidate: first full-game attempt

[Run41261735431](https://github.com/Russianranger/s3ce/actions/runs/41261735431)
remains failed at the requested reverse-landscape observation. Both raw Main
window records available around this check report actual rotation90; requested
settings and sensor input do not establish rotation270. Complete artifact
13066150246 is87,035,779 bytes, ZIP SHA256
`db39606869d00baf86a7790b1183a2bd92464623e606c9ce68b4e30eeb3d44cb`;
all 1,255 members were independently verified. Original gate=false is retained.
Subsequent AOSP source review identifies reversed acceleration directions in
the harness: positiveX yields rotation90 and negativeX rotation270. The corrected
stimulus requires fresh actual window/visible-frame evidence; no APK change is
needed for that test correction.

Before that failure, two process-cold menus render correctly (PIDs4175/6219,
zero startup failures), at actual child[360,0,2280,1080] on2640×1080. Normal
female creation/traits/name/house, actual SaveQuit and new-process saved-Sim
load6219→11637 are visible. Both save mtimes advance1793497478→1793497722.
The restricted visual SaveQuit witness correctly identifies two actual full
main-menu captures while retaining the stale raw observer separately.

Home returns to the same PID11637 and child, but its early capture01:51:57.666
is completely black. A later failure capture01:52:35.126 shows the house and
Pause menu correctly. This proves eventual drawing in the session, not an
immediate visible Home return. A bounded actual-PNG readiness check and explicit
unavailable-rotation record are needed before continuing interactive validation.
No live object/HUD checks or normal Quit were reached in this failed attempt.

## Corrected candidate: Android 15 platform acceptance

Current green [run 41263509512](https://github.com/Russianranger/s3ce/actions/runs/41263509512),
harness-only source 3d486a62bf9023be12e584a84d1d66aa68b8146c, uses the correct
AOSP sensor directions and exact candidate helper. Artifact13066385908 is
1,548,498 bytes, ZIP SHA256
`2c09f96cb75a19763d6751c141d605a5f85119630f6e83c8211ed42768743d37`;
all 112 members and16 reports were independently verified. Same fixture PID4468
reports actual rotation3, receives a real center DOWN/UP at screen1320,516→
child912,513, then visibly returns at measured rotation1. Both child areas are
1824×1026 at[408,3,2232,1029], with matching rendered pixels and inert margins.
Normal Home restoration, last-valid CANCEL positions and sparse-pointer retirement
also pass. The current enabled stock cutout excludes96px on the left once.

The whole log retains one NexusLauncher ANR before probe startup; no probe PID
has a fatal/ANR or app exception. This is not a claim of globally zero ANRs.
Live WM-resize geometry still uses a separate fresh fixture after retaining the
live CANCEL/coordinate-space limit. Stable visible alignment after removing the
optional stock cutout overlay remains unproved. No original ARM32 game executes
on this64-bit-only API 35 image. Firmware/native-driver acceptance remains a phone
test. The exact current facts and original limitations are in FLIP3_ANDROID15.md
and flip3-runtime-evidence.json.

Earlier green [run 41262144495](https://github.com/Russianranger/s3ce/actions/runs/41262144495),
harness-only sourcedc47ec72646e8e02a63a155f3e08f7a80213ae4a, executes the exact
candidate helper DEX in a separate fixture. Artifact13064894359 is1,570,787
bytes, SHA256`4d34910c3f1b432efea449562d0b1c0852e379dc9c0c7b669c36ba0826c6a6fc`.
Actual center coordinates, owned CANCEL/release positions, retired sparse pointer,
inert black margins, visible same-fixture Home restoration and nonzero cutout
fit pass. Its64-bit-only API 35 image rejects the ARM32 game APK; it does not
execute the original engine. See FLIP3_ANDROID15.md and the JSON evidence index
for measured image/ABI/page/geometry facts and every retained scope limitation.
Dedicated continuous reverse rotation, live-resize geometry and stable visible
restoration after removing the optional stock cutout overlay are not claimed.

The preceding exact-candidate platform run 41261735346 remains red because its
harness used transient pre-fullscreen geometry. Artifact13065955313 is779,619
bytes, SHA256`da9747a203ad24ddfed99393551b6f1ebfcbdb2aed27a2f6b0bb3d7c402141da`.
Actual child-local coordinates were correct. The harness-only settling correction
preserves that attempt and qualifies the later capture, without modifying APK.

## Superseded initial candidate identity

| Identity | Value |
| --- | --- |
| Branch / version | `flip3` / `0.1.14-flip3`, code 114 |
| Frozen APK | `S3CE-0.1.14-flip3-arm32.apk`, 76,770,649 bytes |
| APK SHA256 | `f5a85314647cd3699800dff54a3f9f7c0c67fcffb4eeee5a7d4cea522679bd3c` |
| Source | `6add2b7fbe26d94bbe3bb13ef69275a3e9f14e20` |
| Run | [41259011700](https://github.com/Russianranger/s3ce/actions/runs/41259011700), attempt1 |
| Native source | Identical to accepted0.1.13; path-dependent assertion strings explain relink differences. |

The exact signed bytes reconstruct from the pinned release delta. APK asset,
ARM32 hardening/import/fingerprint, original certificate/package114/target 28,
345 viewport host assertions, atomic patch guards, assembled touch/lifecycle/GL
checks, 24 original orientation DEX paths, 365-method static DEX analysis and
37 runtime harness tests pass. These are host/packaging checks, not Android
execution or Samsung acceptance.

The initial two jobs tested the superseded bytes:

- API 30 ARM32-capable emulator at2640×1080: actual game creation, saved-game
  restart/load, two cold menus, inert margins, Home/return, actual landscape
  rotations, visible UI/action review and clean Quit.
- API 35 framework: measured device ABIs/page size and exact candidate install,
  plus a separate test APK loading the candidate's exact `classes2.dex` helper.
  The SurfaceView fixture tests drawing/input/window contracts; it does not run
  the original game or alter the installable candidate.

The first API 35 job failed before Android boot: the hosted emulator executable
could not load `libpulse.so.0`. Artifact13064695298 (2,540 bytes), ZIP SHA256
`b30fe192cb8eadc96fc3ad82bed746441dc0b7637a02369c59540a4dfea3a021`, retains
that setup failure. It is not Android execution or an APK failure. A separate
platform-only workflow installs the missing host libraries and retries the same
frozen APK without cancelling the active full-game job.

Those bytes were rejected before publication. Record all attempts and original
automated results. No game memory, phases or save contents may be edited to
manufacture progression. Physical Flip3 native-driver/firmware compatibility
remains a final device test after completing the available checks.

## Superseded first candidate

The API 35 retry41259363699 ran Android 15 successfully and established the
expected ARM32 install limitation plus proportional geometry with48px navigation
insets, inert margins, center coordinates, cancellation occurrence and Home return.
Cancellation position was wrong, as described below; it is not accepted.
Its whole job remains red at a simulated-resize validation mismatch involving
Android size-compat coordinates. Artifact13064362924 is1,335,918 bytes, ZIP SHA256
79d26b6be1f2c67f6d9f47a4e9d613737fa57123d61ea976d1c59e332329ae98.

Independent inspection found a production cancellation-coordinate defect: Android
ViewGroup sends CANCEL through a special path without the normal child offset.
The native bridge treats CANCEL as finger release and reads its coordinates.
The host double had modelled that special path incorrectly. This supersedes
APK f5a853…bd3c before publication; it will not be delivered as the candidate.
Correct the owned cancellation boundary and host/platform regressions, rebuild,
and validate the new exact bytes. Keep all original results and artifacts.

The initial full-game job also remains failed: its sparse native scene observer
was stale at the completed SaveQuit boundary. Actual captures show the main menu
and ordinary save mtimes advanced, but no reload, final action, Home/return or
normal Quit is accepted from that failed run. Artifact13065425362 is64,211,893
bytes, ZIP SHA256
`237c83d8bf4c31624a160d422961d940b8c1103e5144d0039c663c6282bb1bb8`.
Both process-cold menus passed (PIDs3806/6059); no startup failures occurred in
those two attempts. The corrected harness can qualify only this exact SaveQuit
boundary with two actual stable main-menu OCR captures, same live process/canvas
and a strictly newer normal progress save. Raw observer fields remain preserved
beside the separately labeled visual conclusion. It does not alter game state.

## Publication receipt

[v0.1.14-flip3](https://github.com/Russianranger/s3ce/releases/tag/v0.1.14-flip3)
is published from 5ffdfdce085edb8c5f5a43a4ec2b9b51bb569a88 by successful
[run 41266934248](https://github.com/Russianranger/s3ce/actions/runs/41266934248).
Root independently downloads the public APK and verifies 76,770,649 bytes/exact
SHA256 ea112…d19b, original certificate 3c3d5fdf…02a0c4, v2/v3, package/code 114/name,
min26/target28 and ARMv7. No rebuild/resign occurred between acceptance and release.
[Direct APK](https://github.com/Russianranger/s3ce/releases/download/v0.1.14-flip3/S3CE-0.1.14-flip3-arm32.apk).
The JSON index records the complete checksum/certificate and immutable release
source. Delivery is complete through verification; next is the short physical
Flip3 test and exported report described above.

The release-stage update also triggered green [platform run 41266934203](https://github.com/Russianranger/s3ce/actions/runs/41266934203) for the unchanged APK/helper/driver. Artifact13067507389 is1,605,018 bytes, SHA256`88c142466ee312f2286d8780d5ba9a9e76215572b004d379ec1047b546075b52`. All112 members/16 reports were verified; samePID4426 actual rotation3/center input/visible rotation1 pass. The repeat has0fatal/ANR lines. Earlier environmental ANR and all resize/overlay-removal limits remain. Detailed primary acceptance stays bound to41263509512.
