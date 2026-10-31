# GL-view CPU bitmap reduction — 0.1.12

The Thor report retains a post-install process exit with Android reason **3,
LOW_MEMORY**, status0, and RSS0. It does not retain that process's startup log or
its peak memory footprint. The preceding native SIGSEGV is hours older and must
remain a separate observation. This change removes a verified unnecessary
allocation; it does not establish that the Thor's low-memory termination is fixed.

Original `AirplayView.surfaceChanged(SurfaceHolder,int,int,int)` line585 always
creates an RGB565 Bitmap at the surface width and height. The same class's
`doDraw()` lines764–766 returns without drawing when `m_UseGL` is true. The GL
methods use the static `AirplayGL` EGL presenter and do not consume this Bitmap.
`surfaceDestroyed()` clears the Bitmap reference. The view's mode is assigned by
its constructor; switching from the startup software view to GL constructs a
new view. GL reinitialization uses the existing EGL path.

At1920×1080, the unused Bitmap's pixel payload is **4,147,200 bytes**
(1920×1080×2, about3.96MiB). That is a calculated payload reduction per GL view,
not a measured RSS/PSS reduction: Android allocator, object, row-stride and GPU
storage costs are separate. The full-size integer pixel array and static cache
remain because the native dimension/reference protocol also uses them.

`patches/apply.py` adds one `m_UseGL` branch around only that Bitmap allocation.
Software views keep the original allocation. Pixel-array allocation/reuse,
`setPixelsNative(width,height,pixels)`, locking, notification, EGL setup,
presentation, surface dimensions and input coordinates remain intact. Repeated
GL surface size changes therefore allocate no CPU Bitmap while continuing the
original native dimension updates.

The patch requires the exact original surfaceChanged method SHA256
`a5e33a204a0be37cceef92dda03314e77de014af98ece892eb341b6d87739c44`.
Already-patched input must reconstruct both the exact original and the exact
inserted guard/target placement; moved targets or changed instructions fail.
Untouched GL init/reinit/term/destroy consumers are fingerprinted; the existing
doDraw replacement already has its own original/expected-body guard. Every
method is validated in memory before any patched file is written.

`patches/verify_surface_memory.py` executes the actual assembled surfaceChanged
DEX with explicit Android Bitmap/Log and native-lock/pixel-publication doubles.
It verifies three repeated/reconfigured GL surfaces allocate zero Bitmaps,
software views preserve allocation and array reuse, new software views reuse
the existing static pixel array, and native dimensions/references plus
lock/unlock/notify ordering are unchanged. The old0.1.11 DEX counterexample
allocates three Bitmaps for the same GL sequence. Optional `--decoded` checks
exact idempotence, tampered originals/opcodes/targets and no file writes on
validation failure. These are host control-flow checks, not ART/EGL execution
or proof that Android will avoid a low-memory kill.
