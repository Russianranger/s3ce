# 0.1.16 close-friend romance — candidate validation

Signed APK: `S3CE-0.1.16-flip3-romance-arm32.apk`, code116,76,774,745 bytes.
SHA256 `f0258cf188b12208cbadaa97e0414feeab5b4fb1a2779bfc6a61452b22eaa6e2`.
Production source `024355d3a6af9e6f45c2c0c663db284470444a32` on flip3.
Validation source `4e87e69d22fd48d5f60a8015be976ff85f894fba`.
Original key/appID/private saves, ARM32/4KiB/min26/target28 are preserved.

Only Good Friend6 and Best Friend7 → Budding Romance8 are added, channel1 at
threshold10 after existing rules. Romantic actions must succeed normally;
friendships do not convert automatically. Existing pairs, jealousy, acceptance,
all later relationship rules and the save format remain unchanged.

Both Java DEX files and the native compatibility ELF are byte-identical to the
physically accepted0.1.15 release. The original engine and every other APK asset
except this exact tuning archive are unchanged. Full packaging/source checks,
original-certificate v2/v3 signature, package/code/SDK/ABI and byte-exact release
transport reconstruction pass. See [evidence index](relationship-runtime-evidence.json).

## Host and original ARM evidence

- Six focused integrity tests independently parse all15 rows, prove only the two
  appended graph rules/counts change, compare all677 unrelated compressed and
  decoded resources, and check fingerprints/idempotence/tamper rejection.
- 764 original ARM executions use the resource extracted from this exact signed
  candidate and exact baseline0.1.15. The actual loader, constructors, resolver,
  vector operations and normal setter execute. All13 NPCs, both relocations,
  original edge boundaries, just-below/exact new threshold and branch priority
  pass.108 intended outcomes change; all other results remain identical. Only
  the selected NPC changes, normal score clearing and notification endpoints run.
  Resource acquisition, unrelated delegated SimWorld consumers, allocation,
  logging, goal/UI/art and scene boundaries are modeled; these are not completed
  Android romantic conversations or save persistence tests.
- Sixteen native sanitizer programs and76 runtime-harness tests pass.
- Independent scoped source/data review found no blocker. A path-dependent
  embedded `__FILE__` string explains an initial native rebuild difference;
  rebuilding unchanged source under the original path reproduces the accepted
  native ELF exactly. The first internal signed APK was superseded before any
  Android testing. The earlier missing-javac packaging failure is also retained.

## Actual Android 15 platform fixture

Green [run43803017954](https://github.com/Russianranger/s3ce/actions/runs/43803017954),
artifact14197631334:1,666,986 bytes/112 CRC-verified members, SHA256
`cd80599c20a28b780a4c85ab6735da89550f399b20bb7c1871a27305e9e3ec0c`.
Root/independent review accepts nine scoped helper checks: inert margins, actual
child-local tap/cancel/multitouch, same-process Home return, resize cancellation
with fresh-fixture resized geometry, actual samePID4447 rotation3/input/visible
rotation1 and stock96px cutout fitted once. Enabled parent[96,0,2640,1032],
child[456,3,2280,1029]; pixel and black-margin checks pass. Zero fatal/ANR.

API35 x86_64/arm64-only image has4KiB pages but rejects the ARM32 game with
NO_MATCHING_ABIS. Exact candidate GameViewport DEX executes in a native-free
fixture; no original game/romance runs on that image. Live resize acceptance
remains scoped to cancellation; geometry uses a fresh fixture. After simulated
cutout removal, pixels are visible but bounds[100,20,2740,1051] are invalid;
post-overlay restoration is not accepted. This known fixture limitation does
not imply a newly changed viewport: its DEX is unchanged from accepted0.1.15.

## Actual full game and next action

Green [run43803018055](https://github.com/Russianranger/s3ce/actions/runs/43803018055),
artifact14198872372:215,554,839 bytes/2,993 CRC-verified members, SHA256
`03ec9401ce3f804b49d0a49a4e0b57afa5a697da5a7bb2e06044c7380c9e3347`.
Root and independent review accept the exact candidate for a focused phone test.
The raw `gate_passed=false` remains unchanged; manual acceptance is separate.
Android11/API30 Google APIs x86 revision16, ARMv7 translation, Emulator31.1.4/
KVM/SwiftShader,3GiB/4KiB,2640×1080; actual centered child[360,0,2280,1080].

| Check | Actual observation |
| --- | --- |
| Normal startup | Two process-cold launcher/menu checks, PIDs3953/6168, zero failures, data retained. Both menus visually reviewed. |
| Direct Main | Separate freshPID6758, ordered bootstrap→Native Main and visible normal menu; no Bundle restoration simulated. |
| Creation/save/load | Normal female/traits/Alex/house; prefix save mtime1794803087→1794803357. New-process load6758→12750 succeeds. |
| Home | SamePID12750 returns visibly; subsequent ordinary Bed Sit/controls work. |
| Object action | Live5 actual Cheap Bed/Sit row;6queue;7/10/11 show approach completed and settled seated pose with bent knees. Chair taps3/4 do not establish a chair action. |
| Camera | Normal ladder zoom; mode on7; actual pan10→11. Static room crop11→13 is identical over59.30seconds after release. |
| Jewel | Wishes visible12 with camera on,15 with camera off. |
| Post-action save/reload | SaveQuit21–24 advances both files04:29→04:46UTC. NewPID18185 loads Alex26–28 with Mon14:56/four wishes retained. Save format unchanged; this is a candidate-created save, not the user's115 migration. |
| Walking | After reload, actual floor tap29 moves Sim left across the room;30Pause shows the new position. Seated-floor tap18 had no observed movement. |
| Final save and Quit | SaveQuit30–33 advances files04:46→04:51. Quit34/35 returns Native Main, requests Activity finish and resumes Compat116 with Original rendering unchecked. Final04:51 save not reloaded. |

All36 frame hashes/commands and interrupted attempts are retained. Pan8 encounters
New Wish;9Recipes and16Go to Town are dismissed normally. Pause19 encounters
another Wish. Save23/32 and slot27 show transitions; later complete frames establish
success. Sampled observer fields are stale at several boundaries; actual PNGs,
file mtimes and shutdown logs supply the separate evidence. No game/save edits.
Full log44,619,915 bytes, SHA256
`ed8ad77dec041f8107bcd4569f3e897eace314a255f03fad215d748dd8013567`,
has zero fatal/ANR and zero matching game-process Java/loader/audio errors.
Full-game reverse landscape3 remains unavailable on this API30 image; the exact
Android15 helper result above is separate. No physical116 result or completed
new romance gameplay/persistence is claimed.

The user confirms the previous0.1.15 Hot Smooch fix worked with no subsequent
crashes, without a new bounded startup count/version fingerprint. No new physical
0.1.16 result is claimed. This environment has no supplied close-friend save;
actual Good/Best Friend→Budding Romance and relationship save/reload remain a
focused physical test after available checks and publication are complete.

## Publication verified — next action is the phone romance test

Published [v0.1.16-flip3-romance](https://github.com/Russianranger/s3ce/releases/tag/v0.1.16-flip3-romance)
from `566e1c03778e2111c5c86b535881a4be4c7f036a` by green
[run43807354251](https://github.com/Russianranger/s3ce/actions/runs/43807354251).
Root independently downloaded the public APK and SHA256SUMS. Exact76,774,745 bytes
andf0258c…aa6e2 match the tested frozen candidate. Original-certificate v2/v3,
package/code116, min26/target28, ARMv7 and ZIP CRC verify. No rebuild/resign.

[Direct APK](https://github.com/Russianranger/s3ce/releases/download/v0.1.16-flip3-romance/S3CE-0.1.16-flip3-romance-arm32.apk).
Install over without uninstalling or clearing data; Original rendering unchecked.
Use the existing Good/Best Friend save, complete successful romantic interactions
until Budding Romance appears, SaveQuit/reopen and verify status persistence.
Repeat for the other close-friend stage when available. Then normal Hot Smooch,
controls and three cold starts; Home→app icon→Save report→Share report file.
Include NPC/status before/after and screenshots. This is the remaining focused
physical acceptance step; release/public verification are complete.

## Publication-triggered Android 15 repeat — failure retained

[Run43807354248](https://github.com/Russianranger/s3ce/actions/runs/43807354248)
uses the identical candidate after publication. Artifact14199271196 is1,609,389
bytes, SHA256 `45f42e291e4d2864a21ad2836676883e56e2f657a797984e3b4ee9c92cdabbbc`.
The whole repeat is red at `restore original no-cutout-overlay viewport`, with
`TimeoutError: Activity content is outside its reported app-compatible display`
(`flip3_platform.py:728`). This is the previously excluded simulated overlay-
removal path described above, not an observed original-game/romance crash.
The candidate APK/helper DEX are unchanged. Keep this failed run; do not weaken
the strict geometry check or count post-overlay restoration as accepted. The
initial nine scoped checks and independent actual-game acceptance remain the
basis for this focused test release. Complete repeat review is retained privately.

Independent repeat review verifies all105 ZIP members and the same nine earlier
scoped checks, including samePID4338 actual3/input/visible1 and enabled96px cutout.
Zero fatal/ANR. After overlay removal, final parent[100,20,2740,1051] and
child[508,22,2332,1048] remain invalid while teal pixels are visible: identical
bounds to the excluded final state in the initial green run. The later red wait
makes that unaccepted boundary explicit; no validator/code was weakened.

## Durable evidence recovery

Complete QA evidence, including the failed publication platform repeat, is
retained privately as `S3CE-0.1.16-private-QA-evidence.zip` (219,028,366 bytes),
SHA256 `5f69cca088aa4712dccb56a5e40deff70e9c6180df548de0ff4115c5a99104bd`.
It excludes APKs/raw game binaries/assets, signing inputs and save contents.
