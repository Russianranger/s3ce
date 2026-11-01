# Flip3 runtime review in progress

The corrected signed candidate is `0.1.14-flip3` / code114, SHA256
`ea11252f93bdfbf2a9bb5b8a389e524d1dfb342c0eb8cc3f2e2115236634d19b`,
76,770,649 bytes. It corrects the actual API35 CANCEL-coordinate counterexample
and post-POINTER_UP ownership; 689 corrected host assertions, assembled DEX/24
orientation paths and366-method static DEX analysis pass. Fresh Android execution
is pending. The older candidate and its results are retained below.

## Superseded initial candidate identity

| Identity | Value |
| --- | --- |
| Branch / version | `flip3` / `0.1.14-flip3`, code114 |
| Frozen APK | `S3CE-0.1.14-flip3-arm32.apk`, 76,770,649 bytes |
| APK SHA256 | `f5a85314647cd3699800dff54a3f9f7c0c67fcffb4eeee5a7d4cea522679bd3c` |
| Source | `6add2b7fbe26d94bbe3bb13ef69275a3e9f14e20` |
| Run | [41259011700](https://github.com/Russianranger/s3ce/actions/runs/41259011700), attempt1 |
| Native source | Identical to accepted0.1.13; path-dependent assertion strings explain relink differences. |

The exact signed bytes reconstruct from the pinned release delta. APK asset,
ARM32 hardening/import/fingerprint, original certificate/package114/target28,
345 viewport host assertions, atomic patch guards, assembled touch/lifecycle/GL
checks, 24 original orientation DEX paths, 365-method static DEX analysis and
37 runtime harness tests pass. These are host/packaging checks, not Android
execution or Samsung acceptance.

Two parallel jobs are running against these bytes:

- API30 ARM32-capable emulator at2640×1080: actual game creation, saved-game
  restart/load, two cold menus, inert margins, Home/return, actual landscape
  rotations, visible UI/action review and clean Quit.
- API35 framework: measured device ABIs/page size and exact candidate install,
  plus a separate test APK loading the candidate's exact `classes2.dex` helper.
  The SurfaceView fixture tests drawing/input/window contracts; it does not run
  the original game or alter the installable candidate.

The first API35 job failed before Android boot: the hosted emulator executable
could not load `libpulse.so.0`. Artifact13064695298 (2,540 bytes), ZIP SHA256
`b30fe192cb8eadc96fc3ad82bed746441dc0b7637a02369c59540a4dfea3a021`, retains
that setup failure. It is not Android execution or an APK failure. A separate
platform-only workflow installs the missing host libraries and retries the same
frozen APK without cancelling the active full-game job.

Publication is pending actual runtime review. Record all attempts and original
automated results. No game memory, phases or save contents may be edited to
manufacture progression. Physical Flip3 native-driver/firmware compatibility
remains a final device test after completing the available checks.

## Superseded first candidate

The API35 retry41259363699 ran Android15 successfully and established the
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
