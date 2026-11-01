# Flip3 social-event image crash

## Physical evidence

The user's private diagnostic export identifies S3CE 0.1.14-flip3/code 114,
Samsung SM-F711U1, Android 15/API 35, ARM32, 4096-byte pages, Adreno660 and normal
rendering. The user reports good UI and a reported crash during a Hot Smooch attempt. This is
actual Samsung gameplay evidence for the existing viewport. Full report stays
private; no new touch-geometry change is justified.

The retained native failure is SIGSEGV/SEGV_MAPERR at address 0 on Thread-2.
The motion-callback identity independently locates resident game code. The fault
is game+0xd40, a memcpy destination store; LR=game+0xb3144 is in
midp::ByteArrayInputStream::Read (entry +b3108). The register-matching original ARM reconstruction identifies the immutable
M3G Image2D dispatcher at +9c460 as its caller. At+9c480..9c498 the original requests
new byte[pixel_count], then passes the unchecked result to ReadFully. The count
is 1048576 and destination null. A controlled original ARM fixture reproduces
all recorded r0..r12,PC,LR andSP values when that staging allocation fails.

Of 107 shipped Image2D objects, four use 1 MiB pixel payloads: kiss event and three
HUD atlases. Among nine event images, only texture_quad_event_kiss.m3g
(res.dz entry641) is RGBA 512×512 / 1048576 bytes. Others are RGB 512×512 / 786432 bytes.
This strongly connects the user's Hot Smooch crash to the kiss event image.
The report logs neither action ID nor asset name, so this is a correlation,
not a captured social-dispatch trace.

Allocation routes through original new[]+132ca4, veneer+139750/GOT4a168680,
s3eMallocBase and the original runtime bucket allocator. No free-byte/largest
block sample exists at failure; exhaustion versus fragmentation is unresolved.
Android RSS/available physical memory cannot answer that question. GL 0x503 is
not GL_OUT_OF_MEMORY(0x505); no causal link is established. Earlier LOW_MEMORY
and user-requested exits are separate records.

## Ownership correction

The dispatcher already owns the complete serialized object body. Its original
ByteArrayInputStream constructor (+b321c) retains pointer (+8), zero offset (+10),
length (+14), cursor (+1c). Image2D initialization (+a8354) allocates destination
mips; synchronous setters (+a84a0,+a8e54) read/copy pixels and retain no source
pointer. Body deletion is later at +9d75c..9d760, after setter/palette cleanup.

native/image_pixels.c borrows the bounded body slice and advances the stream
cursor instead of allocating/copying duplicate pixel staging. Array-delete is
skipped only for the canonical borrowed slice; other pointers still use original
delete. All profile checks finish before writes; mismatched/partial profiles
refuse. Class/body/offset/length/cursor/count are checked. Malformed bodies use
original owner-cleanup endpoints and return parser failure. Bounded diagnostics
record image dimensions/count and avoided staging allocation. No assets, heap
budgets, social behavior, touch geometry or saves change.

## Other interaction exposure

| Entry | Event image | Pixel bytes | Mapping evidence |
| --- | --- | ---: | --- |
|638|death|786432|asset name/event text|
|639|hired|786432|asset name/event text|
|640|houseupgrade|786432|asset name/event text|
|641|kiss|1048576|asset/text plus reported Hot Smooch and register signature|
|642|marriage|786432|asset name/event text|
|643|persona|786432|asset name/event text|
|644|promotion|786432|asset name/event text|
|645|skillmax|786432|asset name/event text|
|646|woohoo|786432|asset name/event text|

All nine use this shared immutable loader; their duplicate allocation could fail
under engine-memory pressure. English strings separately include Hot Smooch,
WooHoo, Propose Marriage/Get Married and corresponding event titles. Exact
trigger-to-texture native branches are not established merely from those names.
No additional interaction is claimed to have crashed. HUD atlases share the
loader too. The fix therefore covers the observed failure mechanism more broadly
than one social action, while primary mip allocation and unrelated original
social/animation faults remain possible. It is not universal OOM protection.

## Separate restored-activity failures

Two retained Java failures are restored Main activities entering
AirplayThread.initNative without GameBoot.nativeBootstrap, causing
UnsatisfiedLinkError. These differ from the native gameplay crash.
RuntimeBootstrap now serializes process initialization for both Boot and restored
Main. Readiness follows successful load, graphics configuration, native bootstrap
and Airplay class initialization. Main admission follows mandatory Activity
initialization and precedes view/thread creation; onStart respects admission.
Failures display diagnostics without starting the native thread. Existing
launcher rendering preference handles old restored intents missing the extra.
Normal mode and initialized same-process runtime reuse remain preserved.

## Checks and limits

native/tests/emulate_image_pixels.py takes SHA-pinned original inputs, NDK and
Unicorn; no original binary/report is bundled. All 107 original initializers,
setters and mip outputs match using aligned staging versus the unaligned body
slice. Sources remain unchanged/unretained and stack restores. Twelve compiled
production cases cover low/high game and adapter addresses, normal ownership,
malformed cleanup with/without detached palette, fallback delete, saved registers
and parser false-return unwind. Allocator results and malformed cleanup endpoints
are modeled; this is ARM instruction evidence, not social gameplay completion.
native/tests/image_pixels_test.c checks bounded views, integer limits, atomic
profile refusal and idempotence. Final host/DEX/native/Android results belong in
SOCIAL_RUNTIME_ACCEPTANCE.md. Hot Smooch completion with the user's relationship
and save still needs a phone regression; no game phase/save edits are used to
manufacture it. Keep keys, full reports and original asset dumps outside Git.

## Analysis tooling

REA repository instructions and provider guidance were reviewed. No configured
Hopper/Ghidra/IDA native provider was available in this recovered environment.
The existing SHA-pinned S3CE extraction, Capstone, Unicorn and NDK workflows were
used for these narrow native questions; original DEX/resource analysis used the
existing Apktool/dexlib tools. No REA integration or new provider was added.
An independent reviewer additionally executed the original image/palette/stream
cleanup routines in four address mappings, with exact-once frees and preserved
registers/stack. Allocator/free/memcpy endpoints remain modeled. See
[sanitized cleanup receipt](social-cleanup-review.json).
