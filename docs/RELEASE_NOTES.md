S3CE 0.1.8 — trace game callbacks and drag state.

Reopening now works on the Thor. The latest report also confirms that horizontal
swipes reach the native touch handler while frames continue. The remaining
Create-a-Sim swipe failure is unresolved; this is a diagnostic update, not a
verified swipe fix.

The new report records pointer callback registration, callback entry/return,
queued game input and validated drag-state observations. This distinguishes a
missing motion registration from failed callback delivery or a game-state gate.
Callbacks retain their original payload, user data and return values through
the engine's own stack gateways. The working graphics and RAM fixes remain.

Test:

1. Install over the current app without uninstalling or clearing data.
2. Leave Original rendering (diagnostic mode) **unchecked**, then Start game.
3. At Create-a-Sim, drag from the Sim's torso left and right a few times.
4. While that run is still open, tap Report → Save report and send the saved
   report. If needed, reopen the app icon to access Save report.

Same app ID, signing key and data location. Requires ARM32 application support
and 4 KiB memory pages. Android hardware gesture behavior remains unverified.
