The Java bridge patches are exact-method-byte guarded and applied by `apply.py`.
Input, lifecycle, and diagnostic method bodies are kept in `methods/`, with
original fingerprints and destinations in `input_methods.json`.
The six SoundPlayer lifecycle methods use `audio_methods.json` and the same
atomic, exact-method guards. Its original AudioTrack initializer and native
`generateAudio` declaration are additionally pinned in `method_guards.json`.

Input behavior keeps Android pointer IDs as native finger identities and uses
pointer **indices** for coordinate lookup. DOWN/POINTER_DOWN map to engine event
4, UP/POINTER_UP/CANCEL to 5, and MOVE to 6. CANCEL releases every active finger,
including when the text-entry dialog has taken over. Native callbacks remain on
the original UI thread; no new callback concurrency is introduced. The old
reflection path and per-event UI sleep are removed.

`deviceYield` checks the pause predicate while holding the resume monitor before
waiting, preventing an early resume notification from being lost. `onPause`
limits its Object.wait request to 250ms. Other native calls and Java monitor
acquisition can still block; this does not guarantee an always-responsive game
UI. The separate report process exists for that case.

Run the actual assembled DEX touch adapter against host MotionEvent and native
call doubles, plus the latch-controlled lifecycle race model:

```bash
python3 patches/verify_input.py \
  --apk /path/S3CE.apk \
  --dexlib-jar /path/jadx-headless-mcp-0.7.1-all.jar \
  --jdk /path/full-jdk-17
```

The touch harness interprets the method's actual DEX register and branch
instructions with dexlib2. It checks a full swipe, sparse IDs, a second finger,
removal of the first finger, the surviving finger's final UP, and cancellation.
It rejects unsupported instructions. The original supplied APK reproduces the
index/ID failure on this regression. This is an instruction-subset host test,
not execution inside ART or the original native engine.

Diagnostics hooks attach the game overlay after each surface view replacement,
record touch arrival before native dispatch, and record a heartbeat after GL
swap returns or a software canvas is posted. A returned swap call is not proof
that a frame was successfully presented.

The additive public `AirplayThread.compatGlInit(I)V` entry calls the original
private `glInit(I)V` directly, without changing its mutex, UI-view, or surface
ordering. `method_guards.json` fingerprints that untouched original method.
The wrapper records Java entry and exit plus its thread/state, or records the
full Throwable stack before rethrowing the identical object. These records are
synced to `compat-java-gl.log` and included in report exports. Logging failures
are contained and cannot replace the original failure.

The DEX regression above also executes the actual wrapper's success and exception
paths with the original lifecycle injected as a callee. Run the production file
logger's persistence/failure regression separately:

```bash
python3 app/tests/verify_gl_log.py --jdk /path/full-jdk-17 --sdk /path/android-sdk
```

`gl_version_config.py` also sets Android `[S3E] StackSwitch=1` in the exact
hash-guarded app.icf override. The supplied engine creates a game fibre even with
StackSwitch=0; this setting enables its existing import/callback veneers to
return native services to the real Android thread stack. It does not resize the
fibre or change thread identity. The native lazy GL initializer additionally
uses the original stack-switch thunk when entered directly from a GL pointer.

SoundPlayer callbacks and start/stop/pause/resume/volume changes share an explicit
instance monitor, with exception paths releasing it before rethrowing the same
Throwable. A periodic callback must belong to the current, playing AudioTrack.
It rechecks that ownership after native generation to handle reentrant stop,
restart or pause. Stop retires the track field before detaching its listener,
disabling notifications and stopping/flushing/releasing the platform track.
Android can retain an already-queued callback delegate after listener detachment;
the track identity check keeps that delegate from generating or writing audio.
The original buffer sizes, sample rate, priming counts and volume formula remain
unchanged. The original native mixer shutdown calls Java soundStop before freeing
its channel and mix buffers, so an in-flight callback drains before that release.

Run the actual assembled SoundPlayer DEX regression against host AudioTrack and
native-generation doubles:

```bash
python3 patches/verify_audio.py \
  --apk /path/S3CE.apk \
  --dexlib-jar /path/smali-dexlib2-3.0.9.jar \
  --jdk /path/full-jdk-17
```

The regression checks stale callbacks after stop and restart, paused playback,
concurrent stop during generation and write, reentrant lifecycle changes, and
exception identity/monitor release. All six method bodies are preflighted for
allowlisted instructions, full method descriptors and typed fields. Passing
`--expect-original-race` with the earlier unpatched APK reproduces native
generation after stop followed by the null-track write failure. These are host
DEX/control-flow checks; actual Android playback and clean Quit remain runtime
acceptance checks.
