The shutdown-order repair is specific to the original S3E image with SHA256
`8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a`.

The source main cleanup calls `33F74` at `139284`. That function deletes
`midp::DisplayIPhone` and then the global `CacheGLES11`/`CacheGLES20` renderer.
It leaves the renderer global nonzero. Later, main calls DLC-manager cleanup
`5C52C` at `1392D8`. A loaded `DLCPack` can own `midp::ImageIPhone` at `+0x90`:
the original retain/store block is `5A794..5A800`, and pack destructor `C3F44`
releases that reference. The image destructor `B0CE0` reads the global renderer
and its virtual `+0xA8` method to choose the GPU-resource destructor. It therefore
requires a live renderer after the old source order has already deleted it.

`B1494` reloads the renderer independently from the relocated global at
`33FB4`/`B1490`/`B14A0`. The preceding `B1484` Display getter's result is
overwritten; retaining Display longer is unnecessary for this image operation.

| Main source location | Cleanup | Repaired timing |
| --- | --- | --- |
| `139260..13927C` | RuntimeIPhone graph | Unchanged |
| `139280` | Manager at `77F14` | Unchanged |
| `139284` | DisplayIPhone, then renderer at `33F74` | Display unchanged; renderer delayed |
| `139288..139294` | TexturesCache | Unchanged |
| `139298..1392B8` | Main's temporary CIwTexture | Unchanged |
| `1392BC..1392D4` | M3G/Iw subsystem, texture-name and locale cleanup | Unchanged |
| `1392D8` | DLC manager | Unchanged; renderer deleted immediately afterward |
| `1392DC..1392F0` | EASpywareManager | Unchanged |
| `1392F4..139314` | Component callbacks, allocation and platform cleanup, return | Unchanged |

The patch preserves the original Display prefix and POP/BX epilogue, replacing
only the old renderer half with a branch around a 20-byte tail thunk. Main's
DLC call enters that thunk, which passes the game base to the compiled Thumb
helper and preserves main's return LR. The helper calls the original DLC cleanup,
reloads the current relocated renderer global, and performs the same original
conditional renderer deletion through virtual `+4`. It introduces no JNI calls,
heap allocations, cached game-object pointers, or null-callee suppression.

Installation validates the original Display and complete main-cleanup instruction
spans, the DLC entry and pack/image release prefix, and all three relocated
renderer-global aliases. Both modified locations are validated before writing;
a partial prior patch is rejected. The loader must hold its code-allocation lock
and flush the whole executable allocation after installation.

`shutdown_order_test.c` checks source-byte tampering, address/size bounds,
partial-patch rejection, the thunk literals and idempotence. It runs with ASan
and UBSan; LeakSanitizer is disabled in the managed host where process inspection
is unsupported.

`emulate_shutdown_order.py` executes the production patcher and helper compiled
with the Android NDK's production optimization, Thumb/PIC and stack protection.
Its 16 cases cover low/high split code and data mappings, all 12,255 original
S3E relocations, low/high helper addresses, both renderer classes, and CPU/GPU
images. The complete original main cleanup frame and epilogue execute. Display,
DLC manager, pack, image, renderer and EASpywareManager deletion bodies execute;
the old GPU-image order stops at the read of freed renderer memory, while the
repaired order deletes the GPU resource once and each owning object once. Integer
callee-saved registers including R9, D8-D15, SP/LR and stack canaries are checked.

The fixture explicitly supplies one parsed DLC vector entry and an uploaded GPU
resource handle. Filesystem lookup, the final GPU deletion endpoint and unrelated
subsystem termination are modeled boundaries. RuntimeIPhone's graph is already
closed at test entry. Later component termination contains generic registered
callbacks; these tests do not claim to validate every possible callback body.

The Android 13 report's null virtual call at `B0D38` is consistent with this
proven lifetime hazard, but its summary lacks the saved caller stack and cached
pack address, so it does not uniquely identify the live owner in that run.
Successful Quit through the actual Android UI remains a separate acceptance
gate. Normal exit should reach the existing `Native code done. Shutting down`
and Activity-finish path; Android may retain the idle process afterward.

Run the source regression with:

```sh
PYTHONPATH=/path/to/unicorn-and-capstone python native/tests/emulate_shutdown_order.py \
  --source /path/to/game.unpacked --ndk /path/to/android-ndk \
  --output /path/to/shutdown-results.json
```
