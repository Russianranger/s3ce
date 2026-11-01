# Flip3 test candidate — runtime review in progress

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
