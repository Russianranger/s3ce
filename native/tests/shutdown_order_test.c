#define _GNU_SOURCE
#include "../shutdown_order.c"
#include <assert.h>
#include <stdio.h>
#include <sys/mman.h>

static void original(unsigned char *code) {
    memset(code, 0, CODE_EXTENT);
    memcpy(code + DISPLAY_CLEANUP, display_cleanup, sizeof(display_cleanup));
    memcpy(code + MAIN_CLEANUP, main_cleanup, sizeof(main_cleanup));
    memcpy(code + DLC_CLEANUP, dlc_cleanup, sizeof(dlc_cleanup));
    memcpy(code + 0xc3f44u, pack_image_release, sizeof(pack_image_release));
    uint32_t global = 0x61000000u;
    memcpy(code + 0x33fb4u, &global, 4);
    memcpy(code + 0xb1490u, &global, 4);
    memcpy(code + 0xb14a0u, &global, 4);
}

int main(void) {
    unsigned char *code = mmap(NULL, CODE_EXTENT, PROT_READ | PROT_WRITE,
        MAP_PRIVATE | MAP_ANONYMOUS | MAP_32BIT, -1, 0);
    assert(code != MAP_FAILED && (uintptr_t)code < UINT32_MAX - CODE_EXTENT);
    uintptr_t helper = 0x12345679u;
    original(code);
    assert(s3ce_patch_shutdown_order(NULL, CODE_EXTENT, NULL, CODE_EXTENT, helper) == 0);
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT - 1, code, CODE_EXTENT, helper) == 0);
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code + 4, CODE_EXTENT - 4, helper) == 0);
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT - 1, helper) == 0);
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT + 1, helper) == 0);
    assert(s3ce_patch_shutdown_order(code + 1, CODE_EXTENT, code + 1, CODE_EXTENT, helper) == 0);
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT, 0) == 0);
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT, helper & ~1u) == 0);
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT,
        (uintptr_t)UINT32_MAX + 2u) == 0);
    assert(s3ce_patch_shutdown_order((void *)(uintptr_t)0xfffffffcu,
        CODE_EXTENT, (void *)(uintptr_t)0xfffffffcu, CODE_EXTENT, helper) == 0);
    const size_t spans[][2] = {
        {DISPLAY_CLEANUP, sizeof(display_cleanup)},
        {MAIN_CLEANUP, sizeof(main_cleanup)},
        {DLC_CLEANUP, sizeof(dlc_cleanup)},
        {0xc3f44u, sizeof(pack_image_release)},
        {0x33fb4u, 4}, {0xb1490u, 4}, {0xb14a0u, 4}
    };
    for (size_t i = 0; i < sizeof(spans) / sizeof(spans[0]); ++i) {
        for (size_t j = 0; j < spans[i][1]; ++j) {
            size_t at = spans[i][0] + j;
            code[at] ^= 1;
            assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT, helper) == -1);
            code[at] ^= 1;
        }
    }
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT, helper) == 1);
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT, helper) == 2);
    assert(word_at((uintptr_t)code + EARLY_RENDERER) == 0xea000004u);
    assert(word_at((uintptr_t)code + 0x33fa4u) == (uintptr_t)code);
    assert(word_at((uintptr_t)code + 0x33fa8u) == helper);
    assert(!memcmp(code + DISPLAY_CLEANUP, display_cleanup, 0x20u));
    assert(!memcmp(code + 0x33facu, (const unsigned char *)display_cleanup + 0x38u, 8));
    assert(!memcmp(code + MAIN_CLEANUP, main_cleanup, DLC_CALL - MAIN_CLEANUP));
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT, helper + 2) == -1);
    assert(word_at((uintptr_t)code + 0x33fa8u) == helper);
    /* Incomplete prior patch must fail without repairing either location. */
    uint32_t new_call = word_at((uintptr_t)code + DLC_CALL);
    uint32_t old_call = main_cleanup[(DLC_CALL - MAIN_CLEANUP) / 4u];
    memcpy(code + DLC_CALL, &old_call, 4);
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT, helper) == -1);
    assert(word_at((uintptr_t)code + DLC_CALL) == old_call);
    original(code);
    memcpy(code + DLC_CALL, &new_call, 4);
    assert(s3ce_patch_shutdown_order(code, CODE_EXTENT, code, CODE_EXTENT, helper) == -1);
    assert(word_at((uintptr_t)code + EARLY_RENDERER) == display_cleanup[8]);
    munmap(code, CODE_EXTENT);
    puts("Shutdown order patch: source guards, bounds, two-location atomicity, thunk and idempotence passed");
    return 0;
}
