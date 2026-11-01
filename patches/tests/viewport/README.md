# Viewport JVM contract fixtures

`patches/verify_viewport_host.py --jdk /path/to/jdk` compiles the actual production
`GameViewport.java` with the Java files here and executes SDK26/28/30/35 contracts.
The SDK numbers select API guards in the production source. They do not run those
Android versions.

The bounded ViewGroup fixture owns one normal touch target and translates normal
current/historical pointer coordinates into the child's space once. Its CANCEL
fast path deliberately does not translate, matching the actual API35 probe's
finding. Production must convert its owned cancellation copy at that boundary. The viewport
itself remains production code. Tests check actual measurement/layout, nonzero
screen origins, already fitted asymmetric content with still-present root insets,
black margins, sparse pointer IDs, history, cancellation/reentry and lifecycle.
Window doubles reject API30 decor-fit and API28 cutout calls on earlier contracts.
Orientation is a separate manifest/Java-bridge policy and is not fabricated here.

These are not Android framework, SurfaceView, SurfaceFlinger, EGL, ART, native
engine or device tests. Child View dimensions do not independently prove the
native engine accepted them. The separate Android platform probe and actual
gameplay runtime supply that evidence and preserve their own limitations.

The first fixture incorrectly translated CANCEL like normal input. Correcting
that model reproduced the old helper's parent-coordinate cancellation. The
archived-source route (`--source /path/to/GameViewport.java`) retains this
counterexample; `--case ownership` isolates the separate POINTER_UP/then-CANCEL
ownership defect. The repaired source passes689 assertions across the four SDK
contracts. A bounded native-UP observer models the existing MultiTouch behavior
for each CANCEL ID; it is not execution of native JNI or the assembled DEX.
Pointer properties, coordinates and metadata use only the public obtain API;
hidden MotionEvent split/getPointerIdBits methods are not supplied by these stubs.
