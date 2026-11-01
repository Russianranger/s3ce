# Flip3 game surface and input coordinates

The `flip3` branch adapts the accepted 0.1.13 game for an unfolded Galaxy Z
Flip3 in landscape. The user confirms that 0.1.13 runs and its camera/jewel
repair works. That physical observation is preserved; it is not a new startup
reliability count or Android 15 validation of this branch.

## One real surface owns drawing and input

`GameViewport.install(Activity, View)` installs the original `AirplayView` as a
child of a black `ViewGroup`. The child is the largest exact integer 16:9
rectangle in the content area: `u=min(width/16,height/9)`, size `16u` by `9u`,
centered with any odd remaining pixel on the right/bottom. At an available
2640×1080 this is a real 1920×1080 surface with 360-pixel side margins. At
2640×1079 it is 1904×1071, with 368-pixel side margins and four pixels above/below.
These examples use available content dimensions, not an assertion about the
phone's actual cutout/navigation insets.

Window decor owns fitting system bars/cutouts once. The helper requests fitted
decor on API 30+, a black window/navigation background, and cutout mode `NEVER`
on API 28+. It fits its measured content without subtracting root-window insets
again. It does not resize the device display, stretch a GL viewport, install a
fixed backing-buffer size, or apply a second native coordinate transform.
The native software-to-GL view replacement still installs the same wrapper;
`m_View` and `AirplayThread.setView` continue to refer to the original child.

## Original source of native dimensions

The existing analysis was reused after reading REA's repository instructions
and Android/resource/native guides. No connected native REA provider was
available; the focused fallback uses existing Apktool smali and Capstone against
these fingerprinted original inputs:

| Input | SHA-256 |
| --- | --- |
| Original APK | `d42d0bf4a663abc3b1bb2abd0b350d93b6a2fa687a3b902f111a40c38a94f0d0` |
| Original `lib/armeabi/libairplay.so` | `d93bc59497d377a9524aa8b3fa090aec0e32048bec4bb5e50b757c2f7234befe` |
| Unpacked S3E game | `8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a` |

Native addresses below are original ELF virtual addresses. Game addresses are
offsets in its separately loaded code, as in the existing HUD analysis.

1. Original `AirplayView.surfaceChanged(SurfaceHolder,int,int,int)` receives the
   actual holder's width/height, writes `m_Width/m_Height`, and publishes them
   with `setPixelsNative(width,height,pixels)` under the original native lock.
   The existing GL-only unused-bitmap guard and pixel-array protocol remain.
2. JNI `AirplayView_setPixelsNative` at `0x215ec` stores the supplied width at
   `g_s3eAndroidGlobals+0xe0` and height at `+0xdc`; its global literal is
   `0x53af0`. The child surface is therefore the producing boundary.
3. `s3eSurfaceInit_platform` at `0x22fe4` copies those fields to
   `g_s3eSurfaceGlobals+0x2c/+0x30` (`0x5675c`). `reinit_surface` at `0x22e3c`
   copies the same fields and updates stride/orientation.
4. `s3eGL_swapbuffers` at `0x20ff4` compares both stored dimensions with the
   Android surface fields (`0x21000..0x21030`). A change calls `reinit_surface`,
   the existing GL reinit callback, and `s3eSurfaceNotifyRotate` at `0x3d3e0`.
   `s3eSurfaceGetInt` at `0x3cab8` reads the surface globals. The existing
   resize/reinit notification path is preserved.
5. Game `Display::0xae810` reads surface properties 4/5 through import `0x500`,
   records dimensions at `Display+0x20/+0x24`, and derives its uniform scale
   from the smaller of long-edge/480 and short-edge/320. Its input conversion
   `0xae4f0` and inverse rendering conversion `0xae5a0` use the same scale
   about the same center. The working projection-depth correction keeps XY
   unchanged and changes only the projection's Z-scale argument.

The original Java bridge has no `DisplayMetrics` or `Display.getWidth/getHeight`
calls supplying native size. Original ELF string inspection also finds none of
`getDefaultDisplay`, `DisplayMetrics`, `getWidth`, or `getHeight`; the explicit
publication/copy instructions above establish the dimension path. No display
width spoof or global Java touch scaling is required.

## Touch ownership and margins

Android dispatches a child-targeted `MotionEvent` in that child's coordinates.
The original patched `MultiTouch.onTouchEvent` uses `getPointerId(index)` and
`getX(index)/getY(index)` for each indexed pointer, then passes integer coordinates
unchanged to `AirplayView.onMotionEvent(IIII)`. It uses no raw-screen coordinate
getter. JNI `AirplayView_onMotionEvent` at `0x2148c` forwards the supplied X/Y to
the existing pointer functions (`0x371b4`, `0x37684`, `0x37758`), without adding
the window or margin origin.

The wrapper forwards the original event through `ViewGroup`, with pointer
splitting disabled. Normal Android dispatch owns the child translation for all
pointer indices and historical coordinates; the original bridge continues to
consume current samples. The saved current-sample copy is used only for
cancellation, not as a replacement for forwarded move history. Android's
separate CANCEL fast path is normalized explicitly, as established below.

Touches starting in margins are consumed. Moving any active pointer outside the
child, including an excursion recorded in move history, cancels the entire
original gesture and blocks it until final release.
Geometry changes cancel before moving the old child, so the cancellation uses
the old local coordinates. A changed parent screen origin also cancels when
child-relative bounds stay the same. Focus loss, hidden windows and detach cancel.
The existing input-text gate still delivers CANCEL releases. This avoids a
stuck camera/drag when a fold, window change or system UI interrupts a gesture.

## Actual Android CANCEL counterexample and repair

API 35 [run 41259363699](https://github.com/Russianranger/s3ce/actions/runs/41259363699)
loaded the then-candidate helper directly from its fingerprinted DEX. Candidate
`f5a85314647cd3699800dff54a3f9f7c0c67fcffb4eeee5a7d4cea522679bd3c`
is superseded. The retained archive SHA-256 is
`79d26b6be1f2c67f6d9f47a4e9d613737fa57123d61ea976d1c59e332329ae98`.
It demonstrates correct normal child translation, but exposes a cancellation
defect that the first host ViewGroup double had masked:

| Observation | Child X/Y before CANCEL | Received CANCEL X/Y |
| --- | --- | --- |
| Drag leaves child | 139.17, 513 (raw 547.17, 516) | 547.17, 516 |
| Home during touch | 912, 513 (raw 1320, 516) | 1320, 516 |

The original helper passed a parent-local saved event into
`super.dispatchTouchEvent(CANCEL)`. Android's CANCEL path skips the normal child
offset; the received X/Y therefore remained in parent coordinates. The existing
MultiTouch bridge turns every CANCEL pointer into a native UP, so occurrence of
CANCEL alone is insufficient validation. The original probe assertions checked
release occurrence but missed the wrong position. Its later resize timeout is a
separate harness failure; neither issue is relabeled as a passing complete run.

The corrected helper owns one cancellation boundary for incoming CANCEL and
margin/geometry/focus/lifecycle interruptions. It changes the saved event to
CANCEL, offsets that owned copy by the old child's negative left/top once, and
calls `super` so framework touch-target bookkeeping is retired. Normal events
remain unmodified and use normal framework translation. Incoming CANCEL uses
the last valid owned snapshot rather than trusting its supplied coordinates.

Pointer ownership also advances after `ACTION_POINTER_UP`: its ending index is
excluded from the retained snapshot, so a later CANCEL cannot release that ID
twice. The implementation copies remaining `PointerProperties`/`PointerCoords`
through the public 14-argument `MotionEvent.obtain` API. It preserves metadata
and uses raw-coordinate seeding followed by a parent-local offset, preserving
raw screen coordinates even when pointer index zero was the finger removed.
It uses no hidden `split`/pointer-bit APIs. Tests retain sparse IDs 7/31/3, both
ending-index cases, native-UP accounting and the old helper's counterexamples.

Current rebuilt APK SHA-256 is
`ea11252f93bdfbf2a9bb5b8a389e524d1dfb342c0eb8cc3f2e2115236634d19b`;
its `classes2.dex` is
`61daef3156c105392db9046f9564c460379a374c20a3235d5f1391a35d272f30`.
The reviewed helper source SHA-256 is
`cd4c39b560c85ca9e8d40a1dc3fd36d11cc1526b49e2864622477cce9ebd6307`.
These identities pass independent host/assembled checks below. Actual Android15
run41263509512 now verifies corrected CANCEL coordinates, sparse-pointer ownership,
measured rotation3/input/visible rotation1 return, margins and cutout fitting with
these exact helper bytes. Separate ARM32 game run41263509428 verifies the normal
landscape gameplay/UI/save/exit path. Full-game reverse rotation remains unavailable
on the API30 emulator; its captured orientation listener retains zero filtered
sensor values despite accepted emulator stimulus. See FLIP3_RUNTIME_ACCEPTANCE.md
for complete current and superseded attempts and bounded evidence limits.

## Shared UI coverage and evidence limits

Native character creation, traits, game hints/popups, HUD/status/Buy/Wishes,
camera controls, object menus and Pause/save menus draw inside the same real
surface and use the preserved engine dimension/Display mapping. Fitting that
surface keeps their shared X/Y proportions; this is broader than moving a few
individual controls. It does not prove every game button or every phase has
been executed.

The original-ARM Display regression was independently exercised for both low
and high split code/data mappings at 1920×1080, 1904×1071, 1792×1008 and
1136×639. Original initialization, input and inverse rendering execute in all
eight cases. Uniform scales are 3.375, approximately 3.346875, 3.15 and 1.996875;
the preserved depth repair leaves their XY results identical. Sample round trips
retain the original integer/soft-float quantization (up to three pixels).
Surface-property imports and GL service calls are modeled, so these are host
control-flow results, not Android/EGL or physical phone proof.

Two additional original-ARM cases use the API 35 probe's measured 1824×1026
child: the 2640×1080 display's bottom navigation inset is 48 pixels, so available
parent content is 2640×1032 and the fitted child bounds are [408,3]–[2232,1029].
Both low/high mappings compute uniform scale 3.206249952316284 (approximately
3.20625). Input/inverse-render results remain identical before/after the
preserved depth correction: center [912,513] round-trips exactly; sampled corner
[1823,1025] returns [1822,1022] through original quantization. These bring the
independent dimension/mapping cases to ten. They connect measured Android child
geometry to original native calculations on the host, while native engine
execution on API 35 remains unverified.

Independent `verify_viewport_host.py` execution passes 689 assertions across
API-level contracts 26/28/30/35 (171/172/173/173). It compiles the production helper
against explicit Android doubles: exact/nonintegral fit, already consumed
asymmetric insets, nonzero screen origin, both pointer indices and history,
margin entry/exit/reentry, cancellation/recovery, focus/visibility/detach,
resize/origin changes, software-to-GL replacement and pointer ownership after
POINTER_UP. The corrected ViewGroup double reproduces Android's untranslated
CANCEL fast path; the prior helper fails against it. Those doubles model the
framework boundary; they do not execute Android or EGL. Current rebuilt APK
`verify_viewport.py` passes assembled installation order, cancellation/public
pointer-API freshness checks and 24 original orientation paths, plus source
guard reconstruction. Its installation precedes diagnostic attachment and
thread view publication.

Native sources are unchanged from accepted 0.1.13. Initial 114's rebuilt shim
SHA-256 differs only because the PVRTC assertion embeds the absolute worktree
path in `__FILE__`, changing merged read-only strings and consequent references,
unwind/debug/symbol metadata. An independent scratch rebuild with only a macro
prefix map from the new worktree root to the old root reproduces the published
0.1.13 shim byte-for-byte:
`7f8f71e2ea9c1cf08b75be4df7679ccf498390a47b919559a7553f1d31798064`.
This attributes the native difference without changing APK bytes or native logic.

Android `AlertDialog`/`EditText` and the IME have their own platform window
layout. The optional legacy `VideoView` bridge also creates a separate
`WindowManager` overlay using its video rectangle; no new use of that path is
established here. Do not describe either as a native widget inside this child.
Actual runtime review must separately inspect text entry/keyboard dismissal,
representative native UI families, normal actions/save/reload/exit, and surface
behavior during landscape changes and Home/return. Android 15 platform probes
and ARM32 gameplay on an older translated emulator are separate evidence; an
API 35 image without ARM32 support cannot establish Flip3 gameplay acceptance.
Physical Samsung cutout/navigation behavior, folding and its prior save remain
phone validation until observed.
