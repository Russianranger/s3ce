# 0.1.13 camera input runtime review

Exact candidate: `0.1.13-camera-input`, code113, 76,770,649 bytes, SHA256
`ce8c54bffe5deeb00e6c81b3d942bfdd5f5480b63ef281d33b053cc255eb3a5e`.
Production source: `b76f771113032361de079ee360588e0990426c08`.
The follow-up source `537f768540eb962a6e9422a02ec4838c6b00249d` changes only the
bounded runtime harness. It does not rebuild or modify these signed APK bytes.

Environment: Android11/API30 Google APIs x86 revision16 with ARMv7 translation,
Emulator31.1.4/KVM/SwiftShader, 3GiB guest RAM, 4KiB pages, 1920×1080. This is
emulator evidence, not physical Thor/Android13 acceptance. All progression uses
ordinary Android input; no game phases, memory or save contents are written.

## Camera and jewel evidence

[Run41237818263 attempt1](https://github.com/Russianranger/s3ce/actions/runs/41237818263)
uses the production source and exact candidate. Full artifact13057785251 is
151,084,667 bytes; ZIP SHA256
`516be9f902820851afa5236bcddb80dd88b7629e406ff9560ec50e95f4fc437a`.
Root and independent reviewers inspected the full archive and raw PNGs.

| Live frame | Observed result |
| --- | --- |
| 0 | Loaded Sim/house; captured ordinary phase6, HUD flagsFFFFFFFF, camera mode0. |
| 3 | Bottom-right jewel opens the actual Wishes panel, with goals and current wish. |
| 4 | Closing the panel returns to gameplay. |
| 5 | Camera button visibly enables camera mode. |
| 6 | World drag changes camera angle; fresh observer318 records camera mode1. |
| 8 | After the timed hint closes, static scene landmarks match frame6 exactly. |
| 9 | Jewel opens the actual Wishes panel while the camera button stays active. |
| 11 | Camera button returns to its inactive appearance. |
| 12 | Existing zoom slider visibly reduces scene magnification. |
| 13–16 | Bed menu/Sit selection and later standing pose; completed Sit unconfirmed. |
| 20–23 | Later Sim movement and activity icons; no unobstructed completed object pose. |
| 23 | Pause opens normally. |

The release/stability observation includes a temporary Go to Town hint; it is a
bounded test, not an extended uninterrupted drift test. Observer lines286/318
are sampled and retained; later frames can contain stale text. Resulting mode
and panel activation are established by the visible sequence, not by treating
every retained line as a fresh post-command sample. A hint alone does not prove
tutorial phase21. Yellow papers in the lower-right are wishes, not queued actions.

Two process-cold menu attempts visibly pass, PIDs4193/6195, zero failures. The
later saved-game process12732 is a separate restart/load, not a third repeated
menu test. Ordinary female creation, prefix Save/Quit and new-process saved-Sim
load pass. Two previous session archives are retained. Complete logcat has zero
fatal/ANR matches and zero late-audio warnings.

This run remains **failed** because its24-command budget was exhausted before
native Quit. Command24 selected Save and Continue, but the final PNG still shows
the unconfirmed Save Game dialog and saved-file mtimes did not advance. No
post-test save or normal Quit is claimed. Original acceptance remains blocked,
gate_passed=false. The harness now permits40 strictly frame-bound UI commands
under the same deadline and native-Quit guard, with24 host tests passing.

## Follow-up completion

[Run41240915455 attempt1](https://github.com/Russianranger/s3ce/actions/runs/41240915455)
is green. Full artifact13057464438 is118,389,092 bytes; ZIP SHA256
`02615e464bc80ff951dfd536f08cb2243518ef7a189a293c04c9b13edcb8351b`.
Root and independent reviewers checked its actual PNGs and complete archive.

| Follow-up live frame | Observed result |
| --- | --- |
| 0 | Existing candidate-created Sim loads in process13050, normal phase6. |
| 1–3 | Bed menu/first selection interruption; no completion claimed from these. |
| 4 | Repeated visible Sit selection produces travel and sitting transition. |
| 5 | Sim settled on mattress edge, hips supported, knees bent and boots down. |
| 7–8 | Same seated pose after a New Wish popup closes; Pause opens normally. |
| 9–11 | Save/Quit confirmation, loading and rendered main menu. |
| 12–13 | Native Quit confirmation, then Compat113 with Original rendering unchecked. |

The first selection's interruption remains unexplained; yellow wish papers or
vanished rows do not establish dispatch. Repeated selection and the unobstructed
seated pose establish completion. No state was changed to force progression.

Two more cold menu attempts pass, PIDs4039/6206, then ordinary creation/save and
new-process saved load6206→13050. Across both runs: four repeated menu attempts,
zero startup failures, plus two separate saved-game restarts. All are retained.
The post-action normal save advances both `sim3dat0` (2,562 bytes) and `sim3set`
(90 bytes) from21:04 UTC at reload to21:16 at final snapshots. These are runtime
file observations, not edits. No prior-version Thor save was available locally.

The complete follow-up log has zero fatal/ANR and zero late-audio warnings.
Native Main returns21:19:29.260 UTC and requests Activity finish21:19:29.261.
Compat resumes; the retained idle package PID does not mean game Main resumed.
Command14 finish passes the native-Quit guard. Cached SceneGame observer text
after menu/exit is stale and is not treated as a current game scene.

Original automated acceptance remains awaiting visual review, gate_passed=false.
The [evidence index](camera-input-runtime-evidence.json) separately records the
manual decision to publish these exact bytes as a focused Thor test candidate,
the successful follow-up and the first run's complete harness failure.

Physical confirmation of the camera/jewel repair, prior Thor save install-over,
Home/return and LOW_MEMORY reliability remains the user's next short test.
The earlier0.1.12 completed Bed Sit and physical user-confirmed object actions
remain historical evidence. The first0.1.13 run did not establish completion;
the follow-up now does. Neither emulator run certifies physical memory reliability.
