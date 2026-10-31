S3CE 0.1.2 — report export and startup-crash investigation.

0.1.1 crashed during startup on the Thor. The cause is not confirmed; this
release must not be described as a proven startup-crash fix.

Changes:

- **Save report** writes a named .txt file through Android's document picker.
- **Share report file** attaches a real content URI with a filename, size,
  MIME type, and temporary read permission. The old text-only share could not
  be saved by the user's file manager.
- **View / copy report** provides a fallback without a file manager.
- Reports include retained Android process-exit records, available native
  tombstone summaries, persisted logs, and newly captured Java exceptions.
  The previous build's crash may still be retained after installing this update.
- Remove the extra Snapdragon alpha-state workaround added in 0.1.1; all
  original game assets/configuration are now byte-identical to the supplied APK.
- Keep the PVRTC texture conversion and touch corrections. **Original rendering
  (diagnostic mode)** bypasses the new GL hooks to isolate the startup regression;
  missing textures are expected in that mode. Fully close the game before
  switching modes if the previous game process is still alive.

Install over 0.1.1; app ID, signing key, and saved data are unchanged.
ARM32 application support and 4 KiB pages remain required. No game-file import
is needed. New runtime fixes remain unverified on hardware.

First steps:

1. Install the update. Open the app, but **do not press Start game yet**.
2. Tap **Save report**, choose Downloads, keep the suggested .txt filename, and
   confirm. Attach that saved .txt file to this conversation. It may already
   contain the 0.1.1 crash and the last native startup stage.
3. If saving is unavailable, use **Share report file** or **View / copy report**.
4. After preserving the report, try Start game. If it crashes, reopen the app
   icon and save another report. The report launcher runs independently.
5. If asked to compare rendering paths, fully close the game, enable **Original
   rendering (diagnostic mode)**, and retry. Preserve separate reports for each
   mode. Do not clear app data or uninstall.

Build, signature, relocation/import, asset-integrity, tombstone-parser and DEX
checks pass. Actual Android document-provider saving and game execution require
the Thor confirmation; those are not established by host checks.
