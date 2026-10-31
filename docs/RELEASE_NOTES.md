S3CE 0.1.4 — initialize the actual game-window context before GL queries.

The new report showed that 0.1.3 blocked the platform driver crash, but returning
NULL was insufficient: the game immediately passes its extension string to
strlen without a NULL check. That was an incomplete startup fix.

This update invokes the original Airplay window initializer on the game thread
before the first capability query. It uses the existing engine-mutex release,
UI GL-view creation, surface wait, relock, and same-thread eglMakeCurrent flow.
The real context remains the game's rendering context; there is no temporary
pbuffer or fabricated graphics information.

The initializer validates the saved JNI game-thread state and rechecks the
current EGL context and JNI exception state before querying the actual driver.
Failed or recursive initialization stops with an explicit saved diagnostic
instead of continuing into another NULL-string crash. Existing texture, touch,
report saving and shared rendering-mode safety features remain.

Checks passed: independent binary/JNI review, native sanitizer regressions for
initialization/query ordering, recursion and failure cases, ARM compilation,
relocation/import verification, asset/config checks and APK signatures. Actual
Thor window creation and gameplay still need confirmation.

Test:

1. Install over 0.1.3 without uninstalling or clearing data.
2. Leave Original rendering (diagnostic mode) **unchecked**, then Start game.
3. Check whether the menu loads. Check room/backgrounds/hair/eyes and swipe in
   Create-a-Sim; if successful, proceed into the house and save/reopen.
4. If it crashes or hangs, reopen the app icon and Save report again. The new
   log records window-initialization state and EGL/JNI failures, and the report
   includes additional AirplayGL/AirplayView/EGL error output.

Same app ID, signing key and data location. ARM32 and 4 KiB requirements remain.
No additional game-data import is required.
