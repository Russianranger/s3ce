Experimental compatibility candidate for the supplied The Sims 3 Android game.

Requires Android 13–16 **with ARM32 app support and 4 KiB pages**. Primary target:
AYN Thor Max on Android 13. ARM64-only devices and 16 KiB pages are unsupported.
This release has passed build, APK-signature, asset-integrity, relocation, and
import audits. **It has not yet been installed or played on an Android device.**

Changes: ARM32 Airplay compatibility loader, private storage, public screen-wake
API, removal of contacts/location/phone/network permissions, and startup
diagnostics. All original assets are included unchanged. App ID:
`io.github.russianranger.s3ce`, allowing installation beside the original.

Test:

1. Install and open **The Sims 3 CE**. Keep airplane mode on.
2. Reach the menu, create a Sim, enter the house, check touch and audio.
3. Play for five minutes, save, close and reopen; confirm progress persists.
4. Go home for 15 seconds and return; check graphics, touch, and audio resume.
5. On a startup error, use **Share diagnostics**. On a native crash, send logcat
   containing `S3CECompat`, `Airplay`, `AndroidRuntime`, and the crash tombstone.

The original controller behavior is retained; no new controller mapping is
implemented. Keep the existing app data during testing.
