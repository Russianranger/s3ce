S3CE 0.1.7 — correct legacy RAM reporting and trace swipe delivery.

0.1.6 now reaches Create-a-Sim on the Thor with room/hair textures. The remaining
reported problems are an unresponsive swipe tutorial and an insufficient-memory
warning after restarting.

The original RAM reader shifts MemFree KiB into a signed32 byte count. Several
multi-GiB values become negative or zero, causing its signed64 KiB preflight to
reject startup. Actual original ARM execution reproduces that false rejection.
This update parses64-bit values and saturates the legacy result at INT32_MAX.
Real low-memory values remain low; unavailable readings retain the original-1
sentinel. Raw/capped readings are saved in diagnostics. Device confirmation of
the restart correction is still needed.

The swipe cause remains unresolved. Original ARM pointer-handler tests deliver
moves correctly for normal/sparse IDs and a secondary finger. This build keeps
that dispatch behavior and adds bounded Java source/action/input-gate counters
plus actual native JNI pointer-state traces. The report retains128 KiB of native
logs so the initial DOWN and RAM readings survive the input trace.

Checks passed: eight native sanitizer suites, original ARM RAM/preflight and
pointer trace tests, cross-compilation and binary/relocation/import checks,
Java compilation/production counter tests,310-method static DEX analysis, actual
assembled touch wrapper checks, APK signatures and exact release reconstruction.
Working graphics/stack fixes remain.

Test:

1. Install over the current app without uninstalling or clearing data.
2. Leave Original rendering (diagnostic mode) **unchecked**, then Start game.
3. At Create-a-Sim, press on the Sim’s torso and drag left/right a few times.
   If it stays stuck, reopen the app icon and Save report while that run remains.
4. Close/reopen the game once to check the memory warning. If it returns, save
   that report too. The new report includes actual raw/free memory readings.

Same app ID, signing key and data location. ARM32 and4 KiB requirements remain.
