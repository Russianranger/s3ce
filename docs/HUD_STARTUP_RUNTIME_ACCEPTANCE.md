# 0.1.12 runtime review and targeted Thor handoff

Root and two independent reviewers recommend publishing these exact bytes as a
focused Thor test candidate. This is emulator evidence with explicit remaining
hardware and tutorial-state questions, not a full physical-device acceptance.

| Identity | Verified value |
| --- | --- |
| Version | 0.1.12-hud-startup / code 112 |
| APK | 76,770,649 bytes |
| APK SHA256 | b73c15341acbb61e7fa85173eb440650c665a65df57ce1ac46caf0e2d7325b64 |
| Tested source | 6b6ebe2272864839e19b4ba15b216bcfc6979877 |
| Run / attempt | [41230641948](https://github.com/Russianranger/s3ce/actions/runs/41230641948) / 1, job success |
| Full artifact | [13054123340](https://github.com/Russianranger/s3ce/actions/runs/41230641948/artifacts/13054123340), 151,177,325 bytes |
| ZIP SHA256 | c393a882a0890477fc92127cbf1a19994ee740dbff621dc010126b701b96d68c |

Runtime: Android 11/API 30 Google APIs x86 revision 16, ARMv7 native translation,
Emulator 31.1.4/KVM/SwiftShader, 3 GiB guest RAM, 4 KiB pages, 1920×1080.
All commands were ordinary Android UI input; game phases/memory/save contents
were not edited. The [evidence index](hud-startup-runtime-evidence.json) retains
all raw frame hashes, original automated status, startup attempts and limits.

## Observed startup and progression

All four process-cold menu starts visibly render the main menu. Distinct PIDs
4067, 6251, 6883 and 7168 are accounted for, with zero failed attempts and no data
clearing or reinstall between them. This does not reproduce the Thor's memory
pressure or establish hardware startup reliability. A later normal game save
and process restart loads the candidate-created Sim: PID 7168 → 13470.

The ordinary prefix completed female creation, five traits/name Alex, house
entry, camera/input steps, save and saved-game load. The loaded file was created
by this candidate. An upgrade with a save written by 0.1.11 was not executed on
this clean emulator. App ID, private save location and original signing identity
are preserved; the actual prior Thor save remains the next install-over test.

| Raw live frame | Observation |
| --- | --- |
| 3 | Tap at95,330, beyond old raw-X45 bound, opens status panel and Well rested. |
| 4–5 | Chair/Buy tap opens Build Mode hint, then its actual three-action chooser. |
| 9 | Wishes-strip tap leaves gameplay unchanged. No activation result claimed. |
| 10 | Plumbob dispatch reaches the original Go to Town tutorial hint. |
| 14 | Visible Cheap Bed menu, with actual Sit label. |
| 15 | Action accepted; approach/transition only. |
| 16–17 | Sim settled on bed edge, hips supported, knees bent;17 unobstructed. |
| 18–19 | Nearby Pause works; normal post-action Save/Quit confirmation. |
| 20–22 | Save loading, main menu, then normal Quit confirmation. |
| 23 | Compat version112 resumed, original rendering unchecked; native return/finish markers true, fatal count0. |

Wishes activation is source-proven at the corrected original-ARM boundary, but
not demonstrated in this runtime. The original strip accepts normal phase6;
plumbob also accepts phase21 and then follows the town tutorial path. The visible
Go to Town hint is consistent with this source-derived explanation. It does not
prove every prior rejected tap occurred in that exact phase. No tutorial was
bypassed or game phase written to force a result. Check the strip on the user's
existing save, after any ordinary tutorial prompts, in the next Thor test.

Save data `sim3dat0` (2,562 bytes) and `sim3set` (90 bytes) retain the initial
18:55 UTC modification time through reload and advance to19:18 after the
post-action normal save. The complete live log has zero fatal/ANR matches and
zero late-audio generation warnings. Native Main returns19:21:40.709 UTC and
requests Activity finish19:21:40.710. Four nonfatal original surface-cleanup JNI
not-initialised warnings occur afterward; there is no resulting fatal signal.
The retained package PID is idle. Cached SceneGame observer text after menu/Quit
is stale and is not treated as a live-scene observation.

## Diagnostic behavior and limits

Current code112 session records Application/library/bootstrap/Main/native entry,
startup memory checkpoints and normal native return/Activity destruction. The
four earlier process logs remain in complete diagnostic snapshots. All observed
startup lowMemory flags are false; no low-memory kill was reproduced.

The original acceptance.json remains status
runtime-progression-observed-awaiting-visual-review and gate_passed=false.
Manual authorization of the exact targeted test candidate is separately recorded
in the evidence index; no original automated result was rewritten.

New Android Home/return, Android13–16 gameplay, actual portrait rotation,
normal-phase Wishes activation and physical Thor memory-pressure reliability
remain unconfirmed. The short release test resolves the hardware/startup and
existing-save questions without clearing data.
