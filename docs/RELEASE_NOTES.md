S3CE 0.1.5 — direct JNI graphics initialization.

0.1.4 still stopped during startup on the Thor: its original JNI callback returned
without creating a context, and the Java GL initializer produced no entry log.
The legacy dispatcher clears Java exceptions internally, so its clean exception
status did not establish a successful Java call.

This update bypasses that dispatcher for initial window creation. It resolves a
fresh Java wrapper and calls it with an explicit integer argument on the running
engine thread. The wrapper invokes the original GL initializer directly, keeping
its engine-lock release, UI view creation, surface wait and relock sequence.
Java entry/exit markers and any full exception stack are saved in the report.
A real current EGL context is still required before game GL queries.

The old cache layout, JNI slots, Thumb addresses and argument handling were
checked independently and by executing the original ARM instructions with a
mock JNI table. Those checks found no static ABI error. This is a targeted
replacement of the failing startup call; hardware startup is not yet verified.

Checks passed: native sanitizer regressions, original ARM dispatch/exception
execution, Java wrapper and persistent-logging tests, 309-method static DEX
analysis, ARM/import/relocation/asset verification and APK signatures.

Test:

1. Install over the current app without uninstalling or clearing data.
2. Leave Original rendering (diagnostic mode) **unchecked**, then Start game.
3. Check whether the menu loads, then backgrounds/hair/eyes and Create-a-Sim swipes.
   If successful, enter the house and save/reopen.
4. If startup fails, reopen the app icon and Save report. The report now includes
   durable Java GL-entry/exit markers and initialization exception stacks.

Same app ID, signing key and data location. ARM32 and 4 KiB requirements remain.
No additional game-data import is required.
