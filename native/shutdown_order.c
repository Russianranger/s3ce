#include "shutdown_order.h"
#include <string.h>

#define CODE_EXTENT 0x166ad8u
#define DISPLAY_CLEANUP 0x33f74u
#define EARLY_RENDERER 0x33f94u
#define LATE_THUNK 0x33f98u
#define MAIN_CLEANUP 0x139260u
#define DLC_CALL 0x1392d8u
#define DLC_CLEANUP 0x5c52cu

/* Pinned original S3E SHA256:
 * 8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a.
 * Main originally destroys Display/CacheGLES before its DLC manager. A loaded
 * DLCPack owns an ImageIPhone at +0x90; that image's destructor requires the
 * still-live CacheGLES to choose the GPU resource destructor. Preserve Display
 * destruction at its original point, and destroy only CacheGLES after DLC.
 * Fingerprints contain instructions only; relocated literal pools are excluded.
 */
static const uint32_t display_cleanup[] = {
    0xe92d4010u, 0xe59f4034u, 0xe5940000u, 0xe3500000u,
    0x15901000u, 0x128fe004u, 0x15911004u, 0x112fff11u,
    0xe5940004u, 0xe3500000u, 0x15901000u, 0x15911004u,
    0x18bd4010u, 0x112fff11u, 0xe8bd4010u, 0xe12fff1eu
};
static const uint32_t main_cleanup[] = {
    0xe51f4220u, 0xe5940014u, 0xe3500000u, 0x15901000u,
    0x128fe004u, 0x15911004u, 0x112fff11u, 0xe5849014u,
    0xebfcfb23u, 0xebfbeb3au, 0xe59f00d0u, 0xe5900000u,
    0xe3500000u, 0x1bfd2efeu, 0xe59d002cu, 0xe3500000u,
    0x0a000005u, 0xe59d002cu, 0xe28fe00cu, 0xe5900000u,
    0xe5901004u, 0xe59d002cu, 0xe12fff11u, 0xebfdb636u,
    0xebfbf279u, 0xebfc1faeu, 0xebffecddu, 0xebfdd5c9u,
    0xebfd4582u, 0xebfd29f4u, 0xebfc8c93u, 0xe5940020u,
    0xe3500000u, 0x15901000u, 0x128fe004u, 0x15911004u,
    0x112fff11u, 0xebfbc02bu, 0xe59d0034u, 0xebffe666u,
    0xebfbd5ffu, 0xebfdd53du, 0xe28dd044u, 0xe8bd4ff0u,
    0xe3a00000u, 0xe12fff1eu
};
static const uint32_t dlc_cleanup[] = {
    0xe59f0014u, 0xe5900014u, 0xe3500000u, 0x15901000u,
    0x15911004u, 0x112fff11u, 0xe12fff1eu
};
static const uint32_t pack_image_release[] = {
    0xe92d41f0u, 0xe59f1400u, 0xe2805090u, 0xe5801000u,
    0xe5904090u, 0xe3540000u, 0x0a00000bu, 0xe5940000u,
    0xe28fe008u, 0xe5901008u, 0xe1a00004u, 0xe12fff11u,
    0xe3500000u, 0x0a000004u, 0xe5940000u, 0xe28fe008u,
    0xe5901004u, 0xe1a00004u, 0xe12fff11u, 0xe59f03bcu
};

static uint32_t word_at(uintptr_t address) {
    uint32_t value;
    memcpy(&value, (const void *)address, sizeof(value));
    return value;
}

/* Called by a tail thunk on the same original game thread and game stack.
 * No JNI, allocation, new object ownership, cached runtime pointers or virtual
 * call suppression is introduced. This is the original DLC cleanup followed
 * by the exact original renderer-pointer/vtable+4 deleting-destructor path.
 * Reload the relocated global after DLC cleanup, just as the old renderer half
 * loaded its object at the time of deletion. The renderer-null conditional is
 * the original CMP/conditional-delete behavior, not a null-callee workaround.
 */
void s3ce_finish_shutdown(uintptr_t game_base) {
    void (*destroy_dlc)(void) = (void *)(game_base + DLC_CLEANUP);
    destroy_dlc();
    uintptr_t global = word_at(game_base + 0x33fb4u);
    uintptr_t renderer = word_at(global + 4u);
    if (renderer) {
        uintptr_t table = word_at(renderer);
        void (*destroy_renderer)(void *) = (void *)(uintptr_t)word_at(table + 4u);
        destroy_renderer((void *)renderer);
    }
}

int s3ce_patch_shutdown_order(void *allocation, size_t allocation_length,
    const void *flush_start, uint32_t flush_length, uintptr_t thumb_helper) {
    uintptr_t base = (uintptr_t)allocation;
    if (!base || flush_start != allocation || (base & 3u) ||
        allocation_length < CODE_EXTENT || flush_length < CODE_EXTENT ||
        flush_length > allocation_length || base > UINTPTR_MAX - allocation_length ||
        base > UINT32_MAX - CODE_EXTENT || !thumb_helper ||
        thumb_helper > UINT32_MAX || !(thumb_helper & 1u)) return 0;
    unsigned char *code = allocation;
    const size_t early = EARLY_RENDERER - DISPLAY_CLEANUP;
    const size_t late = DLC_CALL - MAIN_CLEANUP;
    if (memcmp(code + DISPLAY_CLEANUP, display_cleanup, early) ||
        memcmp(code + 0x33facu, (const unsigned char *)display_cleanup + 0x38u, 8) ||
        memcmp(code + MAIN_CLEANUP, main_cleanup, late) ||
        memcmp(code + DLC_CALL + 4u, (const unsigned char *)main_cleanup + late + 4u,
               sizeof(main_cleanup) - late - 4u) ||
        memcmp(code + DLC_CLEANUP, dlc_cleanup, sizeof(dlc_cleanup)) ||
        memcmp(code + 0xc3f44u, pack_image_release, sizeof(pack_image_release))) return -1;
    uint32_t global = word_at(base + 0x33fb4u);
    if (!global || (global & 3u) || global > UINT32_MAX - 4u ||
        global != word_at(base + 0xb1490u) || global != word_at(base + 0xb14a0u)) return -1;
    const uint32_t skip_and_thunk[] = {
        0xea000004u, /* B 0x33fac: original POP/BX after Display cleanup */
        0xe59f0004u, /* LDR r0,[pc,#4]: original game base */
        0xe59fc004u, /* LDR ip,[pc,#4]: Thumb native helper */
        0xe12fff1cu, /* BX ip: tail call, retaining main's LR */
        (uint32_t)base, (uint32_t)thumb_helper
    };
    const uint32_t call_thunk = 0xeb000000u |
        (((LATE_THUNK - (DLC_CALL + 8u)) >> 2u) & 0x00ffffffu);
    int old_early = !memcmp(code + EARLY_RENDERER,
        (const unsigned char *)display_cleanup + early, sizeof(skip_and_thunk));
    int new_early = !memcmp(code + EARLY_RENDERER, skip_and_thunk, sizeof(skip_and_thunk));
    uint32_t old_call;
    memcpy(&old_call, (const unsigned char *)main_cleanup + late, sizeof(old_call));
    uint32_t actual_call = word_at(base + DLC_CALL);
    if (new_early && actual_call == call_thunk) return 2;
    if (!old_early || actual_call != old_call) return -1;
    /* Validate both locations before either write. The caller holds its code
     * allocation lock and flushes the whole executable allocation afterward. */
    memcpy(code + EARLY_RENDERER, skip_and_thunk, sizeof(skip_and_thunk));
    memcpy(code + DLC_CALL, &call_thunk, sizeof(call_thunk));
    return 1;
}
