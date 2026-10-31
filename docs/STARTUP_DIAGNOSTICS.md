# Thor startup evidence and retained sessions — 0.1.12

The supplied report identifies S3CE 0.1.11, a 32-bit process on AYN Thor,
Android 13/API 33, with Original rendering unchecked. All times below are
October 31, 2026, America/Chicago (CDT, UTC−05:00). The complete private report
and screenshot are not committed.

## What the report establishes

| Record | Time / evidence | Interpretation |
| --- | --- | --- |
| Previous process 14069 | 13:11:56.278; reason 10, description `installPackageLI` | APK update stopped the old process. |
| Unsuccessful process 25490 | 13:12:07.695; reason **3**, status 0, no tombstone | Android **LOW_MEMORY** termination. `EXIT_SELF` is reason 1, not 3. This is the latest retained unsuccessful attempt and is temporally consistent with the user's first-start failure. |
| Successful process 26391 | Boot 13:12:10.727; native initialization successful | A retry reached rendering and SceneGame input. The user confirms existing-save continuation and several object interactions. |
| Older process 29276 | 07:41:31; reason 5/status 11; PC=0, LR/game return offset `0xb0d3a` | Older native null-call failure, before the latest installation. It matches the already-documented ImageIPhone destruction path, not the latest low-memory termination. |
| Successful process lifecycle | Pause 13:15:04; return 13:16:47; new EGL context by 13:16:48.100 | This physical session exercised background/return without a captured fatal signal. Exact user action causing backgrounding is not recorded. |
| Successful process exit | Native return 13:17:06.810; Activity destruction complete 13:17:07.500 | Normal engine return/Activity shutdown is visible in this session. |

The successful process reports approximately 2,533,444 KiB free RAM out of
15,621,188 KiB total when the compatibility loader queries memory. That is
not a measurement of the killed process's peak, and does not establish which
allocation or competing process caused the low-memory termination. No new
Thor repeated-start reliability claim follows from a successful retry.

The old emulator ARM-translation VADDL abort is separate evidence. Its signature
is neither the latest LOW_MEMORY record nor the older physical native SIGSEGV.

## Why the unsuccessful launch lost its logs

`GameBootActivity.writeBootLog` previously used truncating `Files.write` for
every phase. `nativeBootstrap` opens `compat-native.log` with `fopen(...,"w")`
once per game process. A successful retry therefore replaced the failed
process's boot/native evidence. The previous report exporter read only current
logs. Android exit history retained the low-memory reason, but no per-attempt
build, phase or memory checkpoints remained for process 25490.

## New diagnostics

The main-process `Application.onCreate` now creates `compat-session.log` before
any Activity or native bootstrap. Its header records package version/code,
installation/update time, process name/PID, 32/64-bit status, and wall/elapsed
startup times. Before current diagnostic files can be reset, bounded copies of
the previous process's session/boot/native/events/GL/Java-crash logs are kept in
`compat-sessions/before-<new-wall-time>-<new-pid>/`. Four previous processes are
retained, including legacy logs from an older APK without a session header.
Only diagnostic files are rotated; saves, application ID and data directories
are untouched. The launcher process never rotates game logs. Report reads are
read-only and expose incomplete snapshots explicitly.

Boot phases append and sync at library load, graphics configuration, native
bootstrap entry/return, original Java class initialization, and Main Activity
launch. The guarded original `AirplayThread.run()` adds durable **Native Main
ENTER** immediately before its original argument preparation and **Native Main
RETURN** immediately after `runNative` returns. Its original three locals,
arguments, native invocation, cleanup and exception propagation remain intact.
Activity lifecycle transitions and uncaught Java errors also persist. The crash
handler is installed before optional session initialization. Diagnostic errors
are best-effort and do not replace the engine's startup or shutdown behavior.

A few startup checkpoints record Android global available/total RAM, low-memory
threshold and flag, process PSS, and Java used/maximum heap. These are explicit
startup measurements, not per-frame probes or claims about unobserved peaks.
Exit reasons retain raw numeric values and add labels using Android constants.
The exporter places current/previous session evidence before exit records and
current logs, with a 1 MiB final bound. Archive files and exported tails have
separate small bounds; reports mark omitted leading bytes.

## Validation and next physical evidence

`app/tests/verify_sessions.py` executes production file persistence/export code
on the host JVM. It checks legacy migration before log reset; failed-process
identity/phase retention after a successful retry; same-process idempotence;
four-process retention; bounded native and oversized session logs; complete
identity export; read-only reporting; save-file preservation; archive-failure
reporting without erasing originals; and Android reason 3/1/5 labels. The
production Java sources also pass the existing GL logger regression.

`patches/verify_native_session.py` executes the candidate's assembled `run()`
DEX against modeled Android/native call boundaries. It checks the original
argument values and dispatch, register count, marker ordering, original normal
cleanup, and propagation of the same injected Java failure without a false
normal-return marker. This supplements static method fingerprints; it does not
execute the game engine or establish actual Android startup success.

These checks validate diagnostics, not startup reliability. Actual Android
candidate startup attempts and gameplay remain separate release evidence.
On the next Thor test, use the existing save and export **Save report** after
any failed start and the successful retry. Compare each PID/build/phase with
its exit record and memory checkpoint. A LOW_MEMORY record still establishes
termination cause, not the exact allocation or a completed reliability fix.
