#include "context_menu.h"
#include <string.h>

#define CODE_EXTENT 0x166ad8u
#define RENDER_HEAD 0x857acu
#define RENDER_TAIL 0x86310u

/* Exact source S3E SHA256:
 * 8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a.
 * All fingerprint words below are instructions, not relocated literal pools.
 * The context menu already draws its rows using Display's anchored Y transform.
 * Its original coarse hit rectangle instead starts at zero, excluding every
 * visible row at high display scales. Only that menu's rectangle is corrected.
 */
static const uint32_t render_head[] = {
    0xe92d4ff0u, 0xe59f5b8cu, 0xe1a04000u, 0xe1a0a001u, 0xe5950000u,
    0xe24dd064u, 0xe3a02002u, 0xe3a010ffu, 0xeb00a2fbu, 0xeb030f7du,
    0xe59f8b6cu, 0xe3a02002u, 0xe5880000u, 0xe5950000u, 0xe3a0108au,
    0xeb00a31au, 0xeb030f76u
};
static const uint32_t render_tail[] = {
    0xe59f0030u, 0xe5900000u, 0xeb030c60u, 0xe3a03d05u, 0xe1a01000u,
    0xe58d3000u, 0xe3a030c8u, 0xe3a02000u, 0xe1a00004u, 0xebffee22u
};
static const uint32_t display_y[] = {
    0xe92d41f0u, 0xe1a04000u, 0xe5900024u, 0xe24dd008u, 0xe1a05001u,
    0xe58d0004u, 0xe5941020u, 0xe1a06002u, 0xe1510000u, 0xa28d0004u,
    0xb1a0000du, 0xe58d1000u, 0xe5900000u, 0xe0800fa0u, 0xe1a070c0u,
    0xe1a00007u, 0xeb026c4bu, 0xe5944000u, 0xe1a01004u, 0xeb026b64u,
    0xe1a08000u, 0xe3a015feu, 0xe1a00004u, 0xeb026dc9u, 0xe1a01008u,
    0xeb026c9eu, 0xeb026bf6u, 0xe3560000u, 0x0a000003u, 0xe3560002u,
    0x1a000002u, 0xe1550007u, 0xaa000000u, 0xe2600000u, 0xe0450000u,
    0xe28dd008u, 0xe8bd41f0u, 0xe12fff1eu
};
static const uint32_t convert_int[] = {
    0xe1b02bc0u, 0xe1a03400u, 0x13833102u, 0x4a000003u
};
static const uint32_t set_bounds[] = {
    0xe59dc000u, 0xe2800030u, 0xe880100eu, 0xe12fff1eu
};
static const uint32_t render_return[] = {0xe28dd064u, 0xe8bd4ff0u, 0xe12fff1eu};

static uint32_t word_at(uintptr_t address) {
    uint32_t value;
    memcpy(&value, (const void *)address, sizeof(value));
    return value;
}

/* Entered on the original, 8-byte-aligned game stack. No JNI, heap allocation,
 * cached game pointers, or floating-point ABI conversion is introduced. Original
 * soft-float integer conversion, Display transform, and rectangle setter execute.
 * Both literal slots were already dereferenced by this same render function.
 */
void s3ce_context_menu_bounds(void *menu, uintptr_t game_base) {
    uintptr_t display_slot = word_at(game_base + 0x86344u);
    uintptr_t style = word_at(game_base + 0x86348u);
    void *display = (void *)(uintptr_t)word_at(display_slot);
    int32_t (*to_int)(uint32_t) = (void *)(game_base + 0x1494a0u);
    int32_t (*anchor_y)(void *, int32_t, int32_t) = (void *)(game_base + 0xae458u);
    void (*rectangle)(void *, int32_t, int32_t, int32_t, int32_t) =
        (void *)(game_base + 0x81bc4u);
    int32_t x = to_int(word_at(style));
    int32_t y = anchor_y(display, 0, 2);
    rectangle(menu, x, y, 200, 320);
}

int s3ce_patch_context_menu(void *allocation, size_t allocation_length,
    const void *flush_start, uint32_t flush_length, uintptr_t thumb_helper) {
    uintptr_t base = (uintptr_t)allocation;
    if (!base || flush_start != allocation || (base & 3u) ||
        allocation_length < CODE_EXTENT || flush_length < CODE_EXTENT ||
        flush_length > allocation_length || base > UINTPTR_MAX - allocation_length ||
        base > UINT32_MAX - CODE_EXTENT || !thumb_helper ||
        thumb_helper > UINT32_MAX || !(thumb_helper & 1u)) return 0;
    unsigned char *code = allocation;
    if (memcmp(code + RENDER_HEAD, render_head, sizeof(render_head)) ||
        memcmp(code + 0xae458u, display_y, sizeof(display_y)) ||
        memcmp(code + 0x1494a0u, convert_int, sizeof(convert_int)) ||
        memcmp(code + 0x81bc4u, set_bounds, sizeof(set_bounds)) ||
        memcmp(code + 0x86338u, render_return, sizeof(render_return))) return -1;
    uint32_t replacement[] = {
        0xe1a00004u, /* MOV r0,r4: original menu */
        0xe59f100cu, /* LDR r1,[pc,#12]: game allocation base */
        0xe59fc00cu, /* LDR ip,[pc,#12]: Thumb C helper */
        0xe12fff3cu, /* BLX ip: preserve normal ARM/Thumb interworking */
        0xea000004u, /* B 0x86338: original stack/register epilogue */
        0xe1a00000u, (uint32_t)base, (uint32_t)thumb_helper,
        0xe1a00000u, 0xe1a00000u
    };
    if (!memcmp(code + RENDER_TAIL, replacement, sizeof(replacement))) return 2;
    if (memcmp(code + RENDER_TAIL, render_tail, sizeof(render_tail))) return -1;
    memcpy(code + RENDER_TAIL, replacement, sizeof(replacement));
    return 1;
}
