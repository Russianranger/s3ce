S3CE 0.1.1 — graphics, touch, and accessible diagnostics update.

Requires Android 13–16 **with ARM32 app support and 4 KiB pages**. Primary target:
AYN Thor Max on Android 13. ARM64-only devices and 16 KiB pages are unsupported.
Version 0.1.0 reached the menu and Create-a-Sim on the Thor, but had missing
backgrounds/hair/eyes and unresponsive swipes. This update addresses identified
causes; **the new fixes still need device testing**.

Changes:

- Software PVRTC texture conversion when the GPU lacks that format. The affected
  assets include the title background, Create-a-Sim room, hair, and eyes.
- Enable the game's existing Snapdragon alpha-state workaround on Android.
- Correct finger ID/index handling, release canceled touches, remove the UI
  input sleep, and guard against a lost resume notification.
- Add an in-game Report button and a separate launcher process for diagnostics.
  Reports include graphics capabilities/errors, input/frame counters, and
  stalled UI-thread snapshots where available.

Install over 0.1.0; the app ID and signing certificate are unchanged. Do not
uninstall or clear app data. Original game assets are unchanged except for the
guarded alpha-workaround configuration addition. No game-file import is needed.

Test:

1. Install the update, open **The Sims 3 CE**, and tap **Start game**. Keep
   airplane mode on.
2. Check whether menu backgrounds/buttons, the room, hair, and eyes now appear.
3. At the Create-a-Sim tutorial, make a continuous left/right swipe over the Sim.
   Check rotation and whether the tutorial advances.
4. If that works, enter the house, check sound/touch, save and reopen. Briefly
   go home and return to check resume.
5. If it stalls, wait about 10 seconds, press Home and tap the app icon again.
   Tap **Share diagnostics**, without pressing Start game again first. The
   report launcher runs separately from the game. The in-game **Report** button
   also opens it while the game UI is responsive.

The original controller behavior is retained; no new controller mapping is
implemented. Keep the existing app data during testing.
