# Character creation crash investigation

Status: the reported crash is unresolved. The UI depth correction is a separate,
source-proven change; the checks below do not establish a crash fix or successful
Android progression beyond character creation.

All offsets refer to the resident ARM code in the original unpacked S3E program,
SHA-256 `8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a`.
No model assets or cast behavior were changed during this investigation.

## Meaning of the fault

The reported PC is `0x13b784`, with fault address `0x38`. The original function
at `0x13b774` casts an object to Group/World (class IDs 9/22):

```asm
13b774  push {r4, lr}
13b778  mov  r4, r0
13b77c  ldr  r0, [r0]
13b780  add  lr, pc, #8
13b784  ldr  r1, [r0, #0x34]
13b788  mov  r0, r4
13b78c  bx   r1
```

The fault therefore indicates an input object's first word/vtable is 4. A null
input object would fault at `0x13b77c`, before this instruction. This evidence
does not distinguish a stale object, overwritten storage or a wrong object
argument. It does not demonstrate a missing female resource.

The function has already replaced LR with `0x13b790` when it faults. Its caller's
return PC is saved at **`[SP+4]`**; R4 preserves the input object. The existing
summary lacks those values. There are 35 direct source callers, so the fault PC
alone cannot identify the responsible call chain. A blanket null-skip would
neither explain nor safely repair this invalid vtable.

## Original model resources

The resource loader `0x8c2e4` uses its literal at `0x8c414` to locate the original
59-byte filename table at resident `0x14d6a0` (unpacked-file `0x15a940`).

| Resource ID | Original file | Objects | Groups | Skinned meshes |
| --- | --- | ---: | ---: | ---: |
| `0xb0` | `scene_cas.m3g` | — | — | — |
| `0xb4` | `sim_female.m3g` | 1241 | 703 | 18 |
| `0xb5` | `sim_male.m3g` | 1229 | 681 | 17 |

Both models have valid serialized Group-child and SkinnedMesh skeleton/bone
references, with no out-of-range references or cycles in those relationships.
Their original bytes were unchanged by the earlier UI strip experiment.

## Bounded original-code checks

Unicorn experiments execute the original ARM implementations for these steps:

1. Parse every female/male object through dispatcher `0x9b98c`, original memory
   stream and typed readers, constructors, reference lookups and COW containers.
2. Retain the selected root, destroy both owning registries, deep-clone through
   `0xa9bc4`, destroy the source root, and traverse the survivor's meshes and
   skeletons through `0x6d704`.
3. Clone a body skeleton and run the original simplifier `0x6e528`.
4. Find body/legs/torso/hair with `0xa9acc`, clone and simplify the parts, run the
   full skinned-geometry merger `0x737b0`, release temporary skins/skeleton,
   clone the merged output, destroy the first output, traverse and destroy its
   surviving duplicate.

The first three checks pass at preferred and high, separately relocated code,
RW data, heap and stack addresses. The split layout applies all 12,255 original
relocation entries. The original Group metadata constructor `0x133440` is
executed from its PREL32 init-array entry.

Step 4 passes these four part-ID combinations per model. Each tuple is
body/legs/torso/hair; maximum available part IDs are included.

| Model | Tested part combinations |
| --- | --- |
| Female | `250/350/450/550`, `250/355/454/555`, `250/351/452/553`, `250/354/453/552` |
| Male | `200/300/400/500`, `200/305/404/504`, `200/301/402/503`, `200/304/403/502` |

Freed allocations are immediately poisoned. The replacement-ownership runs also
reuse freed blocks of exactly matching size (8727 female / 8796 male reuse
allocations) and reject unknown or duplicate frees. No invalid Group cast or
ownership failure occurs in these paths.

These are analysis experiments, not a self-contained public regression suite.
The complex scratch fixtures depend on extracted original models and a source
dispatcher harness, so they are not presented as runnable repository tests.
Only allocation/free boundaries, memcpy and inert diagnostics/atexit are
modeled; constructors, parsing, cloning, simplification, geometry merging and
reference-counted destruction execute original code. The tests do not execute
the complete CAS controller, texture/style selection, a real Android GL context,
native platform callbacks or focus/surface recreation. They do not test every
possible part combination.

## Lifecycle evidence and remaining gate

The last sampled scene is phase 13 with a changing character angle. Two focus
pause/resume cycles occur after that sample. Each restores EGL on the old View,
then original native GL initialization recreates the View/context and restarts
menu audio. The crash occurs 25.2 seconds after the final context initialization.
Focus changes alone do not identify the user's action or prove Activity Home,
Report, onStop or onResume callbacks.

The last native input summary is a sampling boundary: the Java watchdog records
75 more touch events afterward and continuing frame advancement near the fatal
time. No late scene/model snapshot identifies which selection or lifecycle path
was active when the cast failed. The report therefore cannot isolate an
immediate female-toggle failure from later interaction or resource recreation.

Validation still requires real Android progression past CAS, including a fresh
process, female/style selection, and a separate focus/surface recreation path.
Any reproduced failure should retain the object/register state and saved caller
needed to locate the invalid reference before changing game behavior.
