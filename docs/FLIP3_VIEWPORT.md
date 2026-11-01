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
consume current samples. Its saved `obtainNoHistory` copy is used only for a
synthetic cancellation, not as a replacement for forwarded move history.

Touches starting in margins are consumed. Moving any active pointer outside the
child, including an excursion recorded in move history, cancels the entire
original gesture and blocks it until final release.
Geometry changes cancel before moving the old child, so the cancellation uses
the old local coordinates. A changed parent screen origin also cancels when
child-relative bounds stay the same. Focus loss, hidden windows and detach cancel.
The existing input-text gate still delivers CANCEL releases. This avoids a
stuck camera/drag when a fold, window change or system UI interrupts a gesture.

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

Independent `verify_viewport_host.py` execution passes 345 assertions across
API-level contracts 26/28/30/35 (85/86/87/87). It compiles the production helper
against explicit Android doubles: exact/nonintegral fit, already consumed
asymmetric insets, nonzero screen origin, both pointer indices and history,
margin entry/exit/reentry, cancellation/recovery, focus/visibility/detach,
resize/origin changes and software-to-GL replacement. Those doubles model the
framework boundary; they do not execute Android or EGL. The initial 114 APK's
`verify_viewport.py` passes assembled installation order and 24 original
orientation paths, plus source guard reconstruction. Its installation precedes
diagnostic attachment and thread view publication. The later history/origin
helper refinement requires a rebuilt APK before actual runtime acceptance.

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
