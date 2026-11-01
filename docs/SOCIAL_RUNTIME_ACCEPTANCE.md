# 0.1.15 Flip3 socials — accepted focused test candidate

Signed APK: S3CE-0.1.15-flip3-socials-arm32.apk, code 115, 76,774,745 bytes.
SHA256 a759fb156efb526149e3c0e3a9ca3bba4d5646aff4198ae8946dbc7947c7f5eb.
Production source e2eac7e24c712ba77469794d9c802422e5e25bdc on flip3.
Original key/package/private data, ARM32, 4 KiB, min26/target28 preserved.

Root and independent scoped reviews accept these frozen bytes. Raw acceptance
retains gate_passed=false; manual review is recorded separately. Publish by
exact reconstruction, without rebuild/resign. See [evidence index](social-runtime-evidence.json),
[game review](social-game-review.json), [startup review](social-startup-review.json)
and [mechanism](SOCIAL_IMAGES.md).

## Actual full game

Green [run 41338479517](https://github.com/Russianranger/s3ce/actions/runs/41338479517),
attempt1/source e2eac7e. Artifact13097214463:193,634,600 bytes,2,551 CRC-verified
members, SHA2560442a771abc9108c2484fc4bf1422e2ea34a41641ea73448e128186e1283a902.
Android11/API30 Google APIs x86 revision16, ARMv7 translation, Emulator31.1.4/
KVM/SwiftShader,3GiB,4096pages,2640×1080. Actual child[360,0,2280,1080] is1920×1080.
All progression uses ordinary UI input; no phase/memory/relationship/save edits.

| Evidence | Observed result |
| --- | --- |
| Normal cold menus | Two attempts, PIDs3871/6193, zero failures, app data retained. |
| Direct Main | Separate freshPID6771, COLD/Boot bypass, ordered bootstrap return→Native Main once, ordinary menu. Root-emulator boundary test, not Bundle restoration. |
| Creation/save/load | Normal female/traits/Alex/house; prefix save mtimes1793559477→1793559770; new-process saved-Sim load6771→12437. Save created115, not prior114 migration. |
| Home | SamePID12437, visible Pause/house, then ordinary gameplay actions. |
| Live3–9 | Zoom; actual Chair/Sit row, queue and settled seated pose; jewel opens Wishes. |
| Live10–16 | Camera on; pan13 changes angle; jewel/Wishes with camera on14. Static crop13→15 identical for93.81s after release; camera off16. |
| Live17 | Sim rises/walks from chair toward tapped kitchen floor with footprint queue/target. Final destination not separately accepted. |
| Live18–21 | Actual SaveQuit/confirmation, black transition20, visible complete menu21. Both saves advance19:02→19:23UTC (minute-precision listing),2562/90bytes. Post-action save not reloaded; earlier candidate reload confirmed. |
| Live22–23,finish24 | Normal Quit dialog then Compat115, Original rendering unchecked, Native Main return and Activity finish. |

Retain unsuccessful/interrupted attempts: chair tap2 has no accepted action;
jewel6 hits timed New Wish; pan11 hits Go to Town; save20 is black/loading. Later
endpoints establish success. Sampled observer fields remain stale through later
menus; actual PNGs, advancing saves and shutdown logs are separate evidence.

Full log43,875,407 bytes/SHA256d98d8c1c4bced813dde4e238963a245f5a83a23dcde42d501d21956ea5b93e20
has zero fatal/ANR and matching game-process Java/link/late-audio warnings. Four
processes apply the image patch;112 borrow messages include nine1MiB loads,
zero body rejection/profile refusal. This proves shared-loader use, not kiss
asset identity or Hot Smooch completion. Original bounded GL0x500 diagnostics
remain; no graphics-error-free claim. Full-game rotation3 remains unavailable
on this API30 emulator; actual Main stays1, with visible return1 retained.

## Host and original ARM checks

Sixteen native programs,64 startup assertions,689 viewport assertions,52 runtime
harness checks,21 platform checks, six exact assembled DEX suites and static
analysis of379 implementations pass. Assets/signature/package/native hardening
and imports pass. All107 original images preserve pixels/mips;12 compiled
ownership/unwind cases and four independent actual-cleanup cases pass. Modeled
boundaries are explicit in [host](social-host-validation.json),
[image](social-image-validation.json) and [cleanup](social-cleanup-review.json)
receipts. They do not substitute for social gameplay.

Next: install over without uninstall/data clear, Original rendering unchecked;
load the existing relationship save, complete Hot Smooch/event picture, other
available socials, save/load/Home and three force-stop/reopen starts. Export
Home→S3CE icon→Save report, then Share report file. Physical115 social completion,
prior user-save migration and universal startup reliability remain unproven.

## Actual Android 15 helper attempts

Both runs use exact candidate a759fb…f5eb / classes2
 e40894f884a9d47ad67811ea8f80055acc75ff73a6472c28008f229d18bcc6f3.
API35 x86_64 image revision9 exposes x86_64/arm64-v8a and no32-bit ABI;
INSTALL_FAILED_NO_MATCHING_ABIS is retained. The SurfaceView fixture executes
the candidate Java helper only. No original ARM32 game runs on this image.

- Run41338479508/source e2eac7e is red at initial geometry: Android size-compat
  placement exceeds its app-compatible display, with scale0.95555556 and the
  system restart prompt. Artifact13095814708 has12 verified members,1006589bytes,
  SHA2564e0e9c82f13ef8c6fc6f953fcfe6b82c563cee82b1140bdc82661ea2bb7cf465.
- Harness-only source c4a0949 records that specific rejected initialization and
  permits one fresh fixture before testing, retaining strict geometry validation.
  No APK/helper/probe-Java change. Run41339309442 needs no such preparation reset.
  Artifact13097111054 has105 verified members,1435190bytes, SHA256
  0578eba6df1185e0593c53a2426d0d9a3a4c1a82f247354bcd5d6218849dfafb.

Root and independent review accept eight supported core fixture checks from the
second run: inert margins, real child-local center input, drag cancellation,
retired sparse pointer, same-process Home return, resize geometry in a separate
fresh fixture, actual reverse-landscape3 and child-local DOWN/UP there. Before
the optional overlay, actual visible rotation1 return is also supported. These
results preserve the existing resize/fresh-fixture boundary; they are not seamless
live-resize or Samsung/native-game certification.

The second whole run remains red. Enabling a developer tall-cutout overlay
supplies new96px display insets before the helper's parent layout updates. Driver
validates that first report; later logs show the correct parent excluding96px
once. Post-overlay removal ends in invalid size-compat placement. No cutout or
post-overlay restoration acceptance is claimed, and no validator is weakened.
This does not establish a product helper regression; physical114 UI is good and
the115 viewport code is unchanged. Future optional overlay testing should retain
initial reports and wait boundedly for strict same-PID state/layout visibility.
