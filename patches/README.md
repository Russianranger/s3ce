The Java bridge patches are exact-method-byte guarded and applied by `apply.py`.
Input, lifecycle, and diagnostic method bodies are kept in `methods/`, with
original fingerprints and destinations in `input_methods.json`.

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
