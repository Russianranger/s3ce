#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../ui_depth.c"

int main(void) {
    const size_t length = 0x169000;
    unsigned char *code = malloc(length), *before = malloc(length);
    assert(code && before);
    memset(code, 0xa5, length);
    memcpy(code + PROJECTION_LOAD, original_scale, sizeof(original_scale));
    memcpy(before, code, length);
    assert(s3ce_patch_ui_depth(NULL, length, NULL, 0x167000) == 0);
    assert(s3ce_patch_ui_depth(code, GAME_CODE_EXTENT - 1, code, GAME_CODE_EXTENT - 1) == 0);
    assert(s3ce_patch_ui_depth(code, length, code + 0x168000, 4096) == 0);
    assert(s3ce_patch_ui_depth(code, length, code, GAME_CODE_EXTENT - 1) == 0);
    assert(s3ce_patch_ui_depth(code, length, code, length + 1) == 0);
    assert(s3ce_patch_ui_depth(code + 1, length - 1, code + 1, 0x167000) == 0);
    void *overflow = (void *)(UINTPTR_MAX & ~(uintptr_t)3);
    assert(s3ce_patch_ui_depth(overflow, length, overflow, 0x167000) == 0);
    assert(!memcmp(code, before, length));
    for (unsigned i = 0; i < sizeof(original_scale); ++i) {
        code[PROJECTION_LOAD + i] ^= 1;
        assert(s3ce_patch_ui_depth(code, length, code, 0x167000) == -1);
        code[PROJECTION_LOAD + i] ^= 1;
    }
    assert(s3ce_patch_ui_depth(code, length, code, 0x167000) == 1);
    memcpy(before + PROJECTION_LOAD + Z_ARGUMENT, z_one, sizeof(z_one));
    assert(!memcmp(code, before, length)); /* Only the exact Z instruction changed. */
    assert(s3ce_patch_ui_depth(code, length, code, 0x167000) == 2);
    assert(!memcmp(code, before, length));
    free(before);
    free(code);
    puts("Guarded UI XY-only scale: exact four-byte change, full profile, bounds, tamper refusal and idempotence: PASS");
}
