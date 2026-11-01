# Galaxy Z Flip3 landscape / Android 15 assessment

The current candidate is `0.1.14-flip3` / code **114**, from source
`2f3aba9f15313deb61f4f1769565da9d77f0f46c`, continuing the user's working
0.1.13 Thor build. It preserves proportional landscape drawing and touch in
one measured game surface. Source/API review, host checks, emulator execution
and Samsung physical results remain separate evidence.

| Frozen candidate | Identity |
| --- | --- |
| APK | `S3CE-0.1.14-flip3-arm32.apk`, 76,770,649 bytes |
| SHA-256 | `ea11252f93bdfbf2a9bb5b8a389e524d1dfb342c0eb8cc3f2e2115236634d19b` |
| Helper `classes2.dex` | `61daef3156c105392db9046f9564c460379a374c20a3235d5f1391a35d272f30` |

The earlier `f5a853...bd3c` candidate is **superseded**: its actual API 35
probe exposed a CANCEL-position defect that the initial host double missed.
The current candidate corrects cancellation coordinates and remaining-pointer
ownership after POINTER_UP. Its bounded API 35 framework/helper validation is
accepted from green [run 41263509512](https://github.com/Russianranger/s3ce/actions/runs/41263509512),
using the same frozen APK and helper DEX. This establishes the observations
and limits below, including the emulator's ARM32 install rejection. The first
platform attempt remains red and retained; superseded results are historical
evidence rather than acceptance of these corrected bytes. Full-game evidence
is recorded separately. See [viewport implementation](FLIP3_VIEWPORT.md) and the
[runtime receipt](FLIP3_RUNTIME_ACCEPTANCE.md).

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

The implemented wide-screen path preserves a centered 16:9 game area. On an
exact 2640 × 1080 available surface without other
insets, that is `[360,0,2280,1080]`; actual device content bounds govern when
insets differ. The same child surface receives drawing and ordinary Android
touch translation; the corrected cancellation boundary retains the last valid
child-local position. The source/host proof and actual Android evidence are
recorded separately in the linked implementation and runtime documents.

Validation of the exact current APK is split as follows:

- **Actual ARM32 gameplay:** existing API 30 Google APIs x86/ARM-native-bridge
  environment at 2640 × 1080, using the candidate's centered game viewport;
  bounded cold menus, ordinary creation/save/reload, actions, Home/return and
  clean Quit. The linked runtime receipt records the actual game attempts and
  accepted scope; the older F5 prefix is not acceptance of corrected bytes.
- **Actual Android 15 framework:** green run 41263509512 booted API 35 Google
  APIs x86_64 r09, measured ABI/native bridge/page size and attempted the exact
  candidate install. The measured emulator rejected it with
  `INSTALL_FAILED_NO_MATCHING_ABIS`. This is an engine-execution blocker for
  that emulator, independently of its measured 4096-byte page size.
- **API 35 helper probe:** the same run executed the exact candidate Java helper
  DEX against real API 35 SurfaceView/layout/inset/touch APIs. Accepted checks
  include cancellation position and remaining-pointer ownership. No original
  ARM32 engine ran in this fixture; Samsung compatibility remains unverified.
- **Samsung One UI 7:** actual ARM32 support, page size, driver/native-loader
  behavior and physical touch remain phone observations until tested there.

Android's official emulator guidance says Android 12/API 31 and later system
images are 64-bit-only; use measured runtime ABI/native-bridge facts rather than
assuming an Android-version label supplies ARM32 execution. [S10] Record the
exact APK/image identities and actual outcomes in the final runtime receipt.

### Accepted bounded API 35 framework/helper observations

Run 41263509512 / attempt 1 / job 124721395082 used harness source
`3d486a62bf9023be12e584a84d1d66aa68b8146c`; production/candidate source remains
`2f3aba9f15313deb61f4f1769565da9d77f0f46c`. Artifact 13066385908 is 1,548,498
bytes, ZIP SHA-256
`2c09f96cb75a19763d6751c141d605a5f85119630f6e83c8211ed42768743d37`.
All 112 extracted members match the archive. All 16 probe reports identify the
same frozen APK/helper DEX, actual `DexClassLoader`, target 28, software drawing,
sensor-landscape request 6, cutout mode NEVER (2), and `failure=null`.

The API 35 Google APIs x86_64 revision 9 image SHA-256 is
`c06a5966e70bb34645e68e7fe0038ed4396bad30e7a378dbdbb1c26d6a351171`.
It reports `x86_64,arm64-v8a`, empty `abilist32`, `zygote64`,
`libndk_translation.so`, and 4096-byte pages. Exact candidate installation
returns `INSTALL_FAILED_NO_MATCHING_ABIS`; this image cannot test the game.

| Actual framework check | Accepted observation |
| --- | --- |
| Initial layout and drawing | 48-pixel bottom navigation inset; parent [0,0,2640,1032], child [408,3,2232,1029], surface 1824×1026. The child visibly draws fixture RGB (30,110,140). Both black-margin interiors are exact RGB zero and taps are inert. |
| Center tap | Raw [1320,516] arrives as child-local [912,513], with DOWN/UP. |
| Drag leaves child | Last valid MOVE and CANCEL retain pointer ID 0 at [33.150390625,513]; no outside MOVE or extra UP is delivered. |
| Remaining pointer | Real-framework sparse-ID sequence DOWN/POINTER_DOWN/POINTER_UP/CANCEL retires ID 7 at index 0; CANCEL contains only ID 13 at local [380,230], raw [788,233]. |
| Home during touch and return | DOWN/CANCEL both retain ID 0 at local [912,513]. The same fixture process resumes; its 1824×1026 child pixels match the initial image exactly (SHA-256 `0b23f405376b03e884f0f57688ebeb8bfad9ecbf20dfbb37e5c3a1dacd43f2b1`). |
| Live resize cancellation | The live owner receives CANCEL at its last local [912,513]. Android then reports nonuniform app-versus-physical size-compat coordinates; resized geometry is accepted only from an explicitly separate fresh fixture. |
| Fresh resized/restored geometry | Fresh 2160×1080 fixture: parent [0,0,2160,1032], child [168,3,1992,1029], surface 1824×1026. A separate fresh 2640×1080 restore returns the original fitted bounds. |
| Reverse landscape and return | Same fixture PID 4468: actual rotation 3 (WindowManager 270 degrees), then rotation 1 (90 degrees). Reverse center DOWN/UP, ID 0, is raw [1320,516] → local [912,513]. Reverse, pre-tap and restored child pixels match the initial/Home fixture hash above; bounds remain [408,3,2232,1029]. |
| Nonzero cutout | At rotation 1, stock tall-cutout overlay produces actual **left** inset 96, parent [96,0,2640,1032], child [456,3,2280,1029], surface 1824×1026 with visible fixture pixels. The excluded cutout is not subtracted a second time. |

The full 9,251,173-byte log retains one **NexusLauncher ANR**, represented by two
matching lines at 02:03:57.736 and 02:03:58.575, before the first probe process
starts at 02:04:05 (emulator log clock). Probe PIDs 2910/4258/4468 have no
fatal/ANR/exception text or helper failures. The environmental ANR is retained;
this is not a claim of globally zero ANRs. A system WindowManager
`DeadObjectException` following intentional fixture force-stop also remains.

The following limits remain explicit despite the green bounded probe:

- Live resize retained app dimensions 2640×1080 while physical dimensions became
  2160×1080. Its cancellation passed; the separate fresh fixture establishes
  resized geometry. This is not proof of seamless live resize presentation.
- After the optional cutout overlay was disabled, the current reports give
  parent [100,20,2740,1051], extending beyond the physical right edge, and child
  [508,22,2332,1048]. Captured child pixels mix black and fixture color rather
  than proving the reported aligned surface. Stable visible restoration after
  overlay removal is **unproved**. Initial, normal Home/return and the measured
  same-process reverse-landscape/return drawing remain separately established.
- The fixture is not ARM32 game execution, Samsung One UI 7 native-driver/ABI/
  page-size proof, folded-window validation or physical phone certification.

### Earlier bounded platform run and corrected rotation stimulus

Green run [41262144495](https://github.com/Russianranger/s3ce/actions/runs/41262144495)
is retained with artifact 13064894359 (1,570,787 bytes), ZIP SHA-256
`4d34910c3f1b432efea449562d0b1c0852e379dc9c0c7b669c36ba0826c6a6fc`.
Its harness source was `dc47ec72646e8e02a63a155f3e08f7a80213ae4a`; APK/helper
bytes were identical to the current candidate. It established its bounded
center/cancellation/Home/cutout observations, while its dedicated reverse test
remained unavailable at rotation 1. The attempted `+9.8:0:0` sensor vector did
not produce the requested rotation 3. A later cutout capture happened at 3,
which established geometry there but did not establish continuous reverse
input/return in that earlier run. Its old optional-overlay-removal black/partial
frames remain historical limitations.

The current run uses corrected `-9.8:0:0` for actual reverse rotation 3 and
`+9.8:0:0` for measured return to 1, with both WindowManager evidence and
same-process visible/input captures. This is a harness stimulus correction;
the frozen production APK/helper bytes are unchanged.

### Retained first platform attempt for the current APK

Run 41261735346 used API 35 Google APIs x86_64 revision 9, system-image SHA-256
`c06a5966e70bb34645e68e7fe0038ed4396bad30e7a378dbdbb1c26d6a351171`.
It measured ABI list `x86_64,arm64-v8a`, empty `abilist32`, `zygote64`, native
bridge `libndk_translation.so`, and 4096-byte pages. The exact ARM32 candidate
failed installation for the ABI mismatch. This does not prove anything about
the Samsung firmware's ABI/page configuration.

The separate probe loaded the exact helper DEX listed above. Its retained
artifact 13065955313 is 779,619 bytes, ZIP SHA-256
`da9747a203ad24ddfed99393551b6f1ebfcbdb2aed27a2f6b0bb3d7c402141da`.
The raw result remains blocked with one completed check: both physical black
margins were inert. Captured settled geometry has a 48-pixel bottom system
inset, parent 2640×1032, child [408,3]–[2232,1029], and 1824×1026 surface.

The probe driver used an earlier transient readiness geometry to choose a
center tap at raw [1320,491]. The actual framework event was child-local
[912,488], exactly raw minus the captured settled child's [408,3] origin.
The failed assertion expected the transient layout's center; this is evidence
of a harness geometry-ownership problem, rather than an observed incorrect
translation for the actual child. Cancellation, Home/return, resize and
remaining-pointer tests were not reached in that attempt and are not credited
to it. Later green runs used an owned stable capture with the same production
bytes. Current run 41263509512 supplies the accepted observations above. The
earlier raw blocked result and artifact remain intact.

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
