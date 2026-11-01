# Galaxy Z Flip3 landscape / Android 15 assessment

Assessment base: source `1561a3b`, following the user's confirmation that
0.1.13 works on the Thor. This scopes a landscape, proportional-touch candidate
for the unfolded Galaxy Z Flip3. Source/API review, host geometry checks,
emulator execution and Samsung physical results are separate evidence.

## Device facts and requirements

Samsung's official specification lists a 6.7-inch main display, **2640 × 1080**
pixels and **22:9** aspect ratio. Rounded corners and the camera hole reduce
usable area. That is the nominal unfolded landscape panel, not a constant to
substitute for the measured game view. The different cover display is outside
this candidate's initial acceptance path. [S1]

Samsung's official **SM-F711U1** history identifies the One UI 7.0 upgrade as
Android 15, initially build `F711U1UEUBKYD9` dated 2025-05-02. At inspection it
also lists Android 15 build `F711U1UESIKZH2` dated 2026-09-03. Samsung says
updates vary by model, country and operator. This proves an official Android 15
release for that variant; it does not identify the user's installed build. [S2]

Neither source proves the installed Samsung firmware exposes **32-bit ARM app
support** or **4096-byte memory pages**. A 64-bit processor does not establish
a 32-bit app ABI. Android documents `Build.SUPPORTED_32_BIT_ABIS` as the device's
supported 32-bit ABI list. [S3]

| Property | Repository fact / acceptance requirement |
| --- | --- |
| Native ABI | `native/build.sh` builds `armv7a-linux-androideabi26`; builder packages `lib/armeabi-v7a/libairplay.so`. Firmware must support `armeabi-v7a`. |
| Process | `GameBootActivity` rejects a 64-bit process. Preserve ARM32. |
| Pages | `native/legacy_loader.c:JNI_OnLoad` obtains `_SC_PAGESIZE` and rejects anything other than 4096. Preserve its bootstrap log. |
| SDK | Builder sets min SDK 26, target SDK 28; Java compiles against platform 35. Compile and target SDK are distinct. Verify final APK badging. |
| Identity | Preserve `io.github.russianranger.s3ce`, existing certificate and private data. |
| Display | Use actual landscape content/view dimensions, including Samsung windowing, navigation or cutout exclusions; drawing and input must share coordinates. |

Android 15 supports devices configured with 16 KiB pages; it does not imply
all Android 15 phones use them. Native compatibility requires appropriate
binary alignment and runtime assumptions. This original runtime's explicit
4 KiB/ARM32 constraints remain even when its shim uses a recent NDK. Changing
ZIP alignment or target SDK alone cannot supply ARM64/16 KiB support. [S4]

## Android 15 installation and API review

Android 15 rejects new installations targeting below API 24. **Target 28 passes
that specific requirement**; min SDK 26 is below Android 15/API 35. This rules
out the old-target install block as an expected cause, without establishing
full runtime compatibility. No low-target install bypass is required. [S5]

Android 15's default edge-to-edge enforcement applies to apps targeting API 35.
This APK retains target 28, so that change does not justify an SDK bump or a
global touch offset. Samsung windowing/navigation can still affect view bounds.
Judge foreground launches against this app's explicit user-driven launch flow,
rather than assuming PendingIntent/background changes break it. [S6]

| Area | Source inspection | Candidate consequence |
| --- | --- | --- |
| Permissions | Manifest requests only `WAKE_LOCK`, `MODIFY_AUDIO_SETTINGS`, `VIBRATE`; no network, shared-storage, overlay or foreground-service permission. No manifest service, notification listener, boot receiver or PendingIntent path is introduced. | No new Android 15 permission/service migration is indicated by the inspected mandatory flow. Keep local gameplay. |
| Launch | Visible launcher explicitly opens `GameBootActivity`; it configures/bootstraps JNI and explicitly opens private Main. Reports open through user action. | Exercise launcher → game and Home → launcher → game. Automatic restart is not reliability proof. |
| Lifecycle | Main handles orientation/screen-size/layout configuration changes. Existing Airplay surface/audio pause/resume fixes remain. | Test view recreation, Home/return and new-process save loading. Fold/close/reopen is a separate physical observation. |
| Saves/logs | Bootstrap supplies `getFilesDir()` to the engine; session/report staging uses private files. | Internal app-specific files do not require storage permission. Preserve private saves. [S7] |
| Save report | `ACTION_CREATE_DOCUMENT` followed by writing the selected URI. | Storage Access Framework uses a user-selected destination without broad storage permission; test a local destination on Android 15. [S8] |
| Share report | Unexported read-only `ReportProvider`, URI grants enabled; sender uses `content:` URI, ClipData and `FLAG_GRANT_READ_URI_PERMISSION`. | Android documents temporary grants for an unexported provider. Test a receiver can read the attachment; do not expose save directories. [S9] |
| Failure reports | Launcher/provider are in `:launcher`; game preserves current/four previous process logs, installed version/code, phases, memory/exit reasons. | Correlate candidate/PID and export failed attempts before history ages out. Keep native-loader failures visible. |
| Native runtime | Original engine/game remain ARM32; loader retains executable mappings, JNI and stack compatibility work. | Samsung firmware must actually permit this path. No physical Android 15 proof exists yet; manifest-only edits are not a native-loader correction. |

No binary re-analysis was needed: the relevant platform facts are explicit in
the manifest, Java bridge, builder and native bootstrap. Existing original-binary
fingerprints continue to own native patch applicability; this assessment does
not change REA tooling or replace those checks.

## Focused evidence required

1. Verify candidate package/version/code, original certificate, target 28/min 26
   and ARMv7 packaging. Update an existing same-signed installation without
   uninstalling or clearing data.
2. Record Samsung model/build, Android version, ABI list and page size. Require
   a 32-bit process and 4096-byte pages. If installation fails first, preserve
   its exact error; do not infer a page-size result from an ABI/install failure.
3. Fully open the phone in landscape. Capture whole screen and actual content
   bounds. Check proportional drawing and visible-center actions at top-left
   status, lower-left Build/menu, bottom-right Wishes/plumbob, camera toggle and
   zoom. Exercise both camera states and a neighboring world/object action.
4. Use a local existing save when available; otherwise create a normal game.
   Walk, visibly complete an action, zoom/pan/release, save, quit and load from a
   new process. Account for every startup failure. Keep Original rendering off.
5. Press Home and return; verify audio, drawing and touch. Start with ordinary
   navigation settings. If changing navigation mode or closing/reopening the
   phone, record those cases separately.
6. Export **Save report** and verify candidate, Samsung/API 35, ABIs and session/
   exit evidence. Test Share report file as an alternative. Keep reports private.

Optional developer checks when an authorized ADB device is actually available:

```sh
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell getprop ro.build.fingerprint
adb shell getprop ro.product.cpu.abilist32
adb shell getconf PAGE_SIZE
adb shell wm size
adb shell wm density
```

## Runtime matrix and limits

The intended wide-screen path preserves a centered 16:9 game area rather than
stretching it to 22:9. On an exact 2640 × 1080 available surface without other
insets, that is `[360,0,2280,1080]`; actual device content bounds govern when
insets differ. The viewport implementation and its tests are separate source
work; this platform assessment does not certify that implementation.

Validation is split deliberately:

- **Actual ARM32 gameplay:** existing API 30 Google APIs x86/ARM-native-bridge
  environment at 2640 × 1080, using the candidate's centered game viewport;
  bounded cold menus, ordinary creation/save/reload, actions, Home/return and
  clean Quit. This establishes wide-display behavior on that environment.
- **Actual Android 15 framework:** boot API 35 Google APIs x86_64 r09, measure
  ABI lists/native bridge/page size, and attempt the exact candidate install.
  Current image metadata indicates no 32-bit ABI; retain any resulting
  `INSTALL_FAILED_NO_MATCHING_ABIS` as a blocker, not an engine test result.
- **API 35 helper probe:** if used, a separate probe may execute exact candidate
  Java helper DEX against real API 35 SurfaceView/layout/inset/touch APIs. It
  cannot establish original ARM32 engine execution or Samsung compatibility.
- **Samsung One UI 7:** actual ARM32 support, page size, driver/native-loader
  behavior and physical touch remain phone observations until tested there.

Android's official emulator guidance says Android 12/API 31 and later system
images are 64-bit-only; use measured runtime ABI/native-bridge facts rather than
assuming an Android-version label supplies ARM32 execution. [S10] Record the
exact APK/image identities and actual outcomes in the final runtime receipt.

## Primary sources

Official pages inspected 2026-10-31 (America/Chicago):

- **S1 — Samsung display specifications:** https://news.samsung.com/global/the-next-chapter-in-mobile-innovation-unfold-your-world-with-galaxy-z-fold3-5g-and-galaxy-z-flip3-5g
- **S2 — Samsung SM-F711U1 updates:** https://doc.samsungmobile.com/SM-F711U1/019608210813/eng.html
- **S3 — Device ABI reporting:** https://developer.android.com/reference/android/os/Build#SUPPORTED_32_BIT_ABIS
- **S4 — Native page-size requirements:** https://developer.android.com/guide/practices/page-sizes
- **S5 — Android 15 minimum target SDK:** https://developer.android.com/about/versions/15/behavior-changes-all#minimum-target-api-level
- **S6 — Android 15 target-gated behavior/insets:** https://developer.android.com/about/versions/15/behavior-changes-15#edge-to-edge
- **S7 — App-specific internal files:** https://developer.android.com/training/data-storage/app-specific
- **S8 — Document creation:** https://developer.android.com/training/data-storage/shared/documents-files#create-file
- **S9 — Provider export/URI grants:** https://developer.android.com/guide/topics/manifest/provider-element#exported
- **S10 — Emulator 64-bit guidance:** https://developer.android.com/games/optimize/64-bit#android_emulator
