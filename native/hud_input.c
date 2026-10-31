#include "hud_input.h"
#include <string.h>

#define CODE_EXTENT 0x166ad8u
/* Source S3E SHA256: 8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a.
 * SceneGame converts stack-held touch coordinates to logical UI space first.
 * Its circle radii must stay in those units. Lower HUD bar bounds instead use
 * original raw coordinates, so their final left/right selection must do so too.
 * Rendering, global conversion, object menus, actions and game state are intact.
 */
static const uint32_t input_head[] = {
    0xe92d4ff0u, 0xe24dd01cu, 0xe59f9728u, 0xe58d1018u,
    0xe58d2014u, 0xe1a04000u, 0xe1a07001u, 0xe1a08002u,
    0xe5990000u, 0xe1a05003u, 0xe28d2014u, 0xe28d1018u,
    0xebfe9c99u,
};
static const uint32_t pause_radius[] = {
    0xe5990000u, 0xe3a01018u, 0xebfe9bddu, 0xe59411c0u,
    0xe3e06000u, 0xe3510006u, 0x1a000025u, 0xe59d2018u,
};
static const uint32_t buy_radius[] = {
    0xe5990000u, 0xe3a01018u, 0xebfe9b90u, 0xe58d0000u,
    0xe59d0018u, 0xe59d1014u, 0xe1a03006u, 0xe1a02005u,
    0xeb005e64u, 0xe3500000u,
};
static const uint32_t sim_radius[] = {
    0xe5990000u, 0xe3a01018u, 0xebfe9b58u, 0xe59411c0u,
    0xe3510006u, 0x13510015u, 0x1a000044u, 0xe58d0000u,
    0xe59d0018u, 0xe59d1014u, 0xe59d2010u, 0xe59d300cu,
    0xeb005e28u, 0xe3500000u,
};
static const uint32_t bar_choice[] = {
    0xe59d1010u, 0xe59d200cu, 0xe1a00004u, 0xebfed4bau,
    0xe59d0018u, 0xe150000bu, 0xaaffffc2u, 0xe1500006u,
    0xd3a01004u, 0xd1a00004u, 0xdbffe13bu, 0xeafffedau,
};
static const uint32_t convert_touch[] = {
    0xe92d41f0u, 0xe1a04000u, 0xe5900024u, 0xe24dd008u,
    0xe1a07001u, 0xe58d0004u, 0xe5941020u, 0xe1a08002u,
    0xe1500001u, 0xe58d1000u, 0xa28d1004u, 0xb1a0100du,
    0xe5911000u, 0xe58d0004u, 0xe0811fa1u, 0xe5940020u,
    0xe1a050c1u, 0xe59d1004u, 0xe58d0000u, 0xe1500001u,
    0xa28d0004u, 0xb1a0000du, 0xe5900000u, 0xe0800fa0u,
    0xe1a060c0u, 0xe5970000u, 0xe0400005u, 0xeb026c1au,
    0xe5941000u, 0xeb026b34u, 0xeb026bccu, 0xe0800005u,
    0xe5870000u, 0xe5980000u, 0xe0400006u, 0xeb026c12u,
    0xe5941000u, 0xeb026b2cu, 0xeb026bc4u, 0xe0800006u,
    0xe5880000u, 0xe28dd008u, 0xe8bd41f0u, 0xe12fff1eu,
};
static const uint32_t circle_hit[] = {
    0xe0402002u, 0xe0410003u, 0xe0030292u, 0xe59dc000u,
    0xe1a02000u, 0xe0010c9cu, 0xe0203092u, 0xe1510000u,
    0xb3a00000u, 0xa3a00001u, 0xe12fff1eu,
};
static const uint32_t rect_hit[] = {
    0xe52d4004u, 0xe99d1010u, 0xe1500002u, 0xa1510003u,
    0xa0822004u, 0xa1520000u, 0xc083000cu, 0xc1500001u,
    0xc49d4004u, 0xc3a00001u, 0xc12fff1eu, 0xe49d4004u,
    0xe3a00000u, 0xe12fff1eu,
};
static const uint32_t status_hit[] = {
    0xe3a01001u, 0xeb0109cfu, 0xeb010717u, 0xe1a06000u,
    0xe1a00004u, 0xeb00a484u, 0xe88d0041u, 0xe59d1014u,
    0xe1a03005u, 0xe3a02000u, 0xe1a00007u, 0xeb005da6u,
    0xe3500000u, 0x0a000010u, 0xe3a06000u, 0xe1a05006u,
};
static const uint32_t status_width[] = {
    0xe92d41f0u, 0xe3a06000u, 0xe1a04000u, 0xe1a05006u,
    0xe5940024u, 0xe1a01005u, 0xebffec24u, 0xe3700001u,
    0x0a00000bu, 0xe5942024u, 0xe1a01000u, 0xe1a00002u,
    0xebffe624u, 0xe5942020u, 0xe1a01000u, 0xe2823e26u,
    0xe3a02003u, 0xe1a00003u, 0xebfcc6b4u,
};
static const uint32_t display_scale[] = {
    0xe92d4010u, 0xe1a04000u, 0xe1a00001u, 0xeb026c9cu,
    0xe5941000u, 0xeb026cf6u, 0xe8bd4010u, 0xea026c4du,
};
struct fingerprint { uint32_t offset; const void *words; size_t length; };
static const struct fingerprint profile[] = {
    {0x107254u, input_head, sizeof(input_head)},
    {0x1073c4u, pause_radius, sizeof(pause_radius)},
    {0x1074f8u, buy_radius, sizeof(buy_radius)},
    {0x1075d8u, sim_radius, sizeof(sim_radius)},
    {0x1077d0u, bar_choice, sizeof(bar_choice)},
    {0xae4f0u, convert_touch, sizeof(convert_touch)},
    {0x11eeb0u, circle_hit, sizeof(circle_hit)},
    {0x11ef00u, rect_hit, sizeof(rect_hit)},
    {0x107834u, status_hit, sizeof(status_hit)},
    {0x130a60u, status_width, sizeof(status_width)},
    {0xae348u, display_scale, sizeof(display_scale)},
};
struct correction { uint32_t offset, before, after; };
static const struct correction fixed_corrections[] = {
    {0x1073ccu, 0xebfe9bddu, 0xe3a00018u},
    {0x107500u, 0xebfe9b90u, 0xe3a00018u},
    {0x1075e0u, 0xebfe9b58u, 0xe3a00018u},
    {0x1077e0u, 0xe59d0018u, 0xe1a00007u},
};

static uint32_t word_at(uintptr_t address) {
    uint32_t result;
    memcpy(&result, (const void *)address, sizeof(result));
    return result;
}

/* The existing raw-X rectangle needs a pixel width; its original width producer
 * is logical. Retain the source's six-unit side margin and scale1 behavior. */
__attribute__((used, noinline))
int32_t s3ce_hud_scaled_status_width(void *scene, uintptr_t game_base) {
    int32_t (*width)(void *) = (void *)(game_base+0x130a60u);
    int32_t (*scale)(void *, int32_t) = (void *)(game_base+0xae348u);
    void *display = (void *)(uintptr_t)word_at(word_at(game_base+0x10798cu));
    return scale(display, width(scene));
}

#if defined(__arm__)
/* LR=game+10784c identifies the guarded BLX call site. Save24 bytes for
 * 8-byte alignment, restore original stack args, and skip the literal word.
 * No JNI, allocation or retained engine pointer is introduced. */
__attribute__((naked)) void s3ce_hud_status_width_gateway(void) {
    __asm__ volatile(
        "push {r1-r5, lr}\n"
        "mov r0, r4\n"
        "movw r2, #0x784c\n"
        "movt r2, #0x10\n"
        "sub r1, lr, r2\n"
        "bl s3ce_hud_scaled_status_width\n"
        "pop {r1-r5, lr}\n"
        "str r0, [sp]\n"
        "str r6, [sp, #4]\n"
        "add lr, lr, #4\n"
        "bx lr\n");
}
#else
void s3ce_hud_status_width_gateway(void) {}
#endif

int s3ce_patch_hud_input(void *allocation, size_t allocation_length,
                        const void *flush_start, uint32_t flush_length, uintptr_t thumb_gateway) {
    uintptr_t base = (uintptr_t)allocation;
    if (!base || flush_start != allocation || (base & 3u) ||
        allocation_length < CODE_EXTENT || flush_length < CODE_EXTENT ||
        flush_length > allocation_length || base > UINTPTR_MAX-allocation_length ||
        !thumb_gateway ||
        thumb_gateway > UINT32_MAX || !(thumb_gateway & 1u))
        return 0;
    struct correction corrections[7];
    memcpy(corrections, fixed_corrections, sizeof(fixed_corrections));
    corrections[4]=(struct correction){0x107844u,0xe1a00004u,0xe59fc000u};
    corrections[5]=(struct correction){0x107848u,0xeb00a484u,0xe12fff3cu};
    corrections[6]=(struct correction){0x10784cu,0xe88d0041u,(uint32_t)thumb_gateway};
    unsigned char *code = allocation;
    unsigned changed = 0;
    for (size_t i=0; i<sizeof(corrections)/sizeof(corrections[0]); ++i) {
        uint32_t word;
        memcpy(&word, code+corrections[i].offset, sizeof(word));
        if (word == corrections[i].after) ++changed;
        else if (word != corrections[i].before) return -1;
    }
    if (changed && changed != sizeof(corrections)/sizeof(corrections[0])) return -1;
    /* Compare complete surrounding instruction spans without accepting a mixed
     * or partially modified generation. Validate every span before any write. */
    for (size_t i=0; i<sizeof(profile)/sizeof(profile[0]); ++i) {
        const unsigned char *expected = profile[i].words;
        for (size_t j=0; j<profile[i].length; j+=4) {
            uint32_t word;
            memcpy(&word, expected+j, sizeof(word));
            if (changed) for (size_t k=0;k<sizeof(corrections)/sizeof(corrections[0]);++k)
                if (profile[i].offset+j==corrections[k].offset) word=corrections[k].after;
            if (memcmp(code+profile[i].offset+j, &word, sizeof(word))) return -1;
        }
    }
    if (changed) return 2;
    for (size_t i=0;i<sizeof(corrections)/sizeof(corrections[0]);++i)
        memcpy(code+corrections[i].offset, &corrections[i].after, sizeof(uint32_t));
    return 1;
}
