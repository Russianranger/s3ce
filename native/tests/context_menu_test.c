#define _GNU_SOURCE
#include "../context_menu.c"
#include <assert.h>
#include <stdio.h>
#include <sys/mman.h>

static void original(unsigned char *code) {
    memset(code, 0, CODE_EXTENT);
    memcpy(code + RENDER_HEAD, render_head, sizeof(render_head));
    memcpy(code + RENDER_TAIL, render_tail, sizeof(render_tail));
    memcpy(code + 0xae458u, display_y, sizeof(display_y));
    memcpy(code + 0x1494a0u, convert_int, sizeof(convert_int));
    memcpy(code + 0x81bc4u, set_bounds, sizeof(set_bounds));
    memcpy(code + 0x86338u, render_return, sizeof(render_return));
}

int main(void) {
    unsigned char *code = mmap(NULL, CODE_EXTENT, PROT_READ | PROT_WRITE,
        MAP_PRIVATE | MAP_ANONYMOUS | MAP_32BIT, -1, 0);
    assert(code != MAP_FAILED && (uintptr_t)code < UINT32_MAX - CODE_EXTENT);
    uintptr_t helper = 0x12345679u;
    original(code);
    assert(s3ce_patch_context_menu(NULL, CODE_EXTENT, NULL, CODE_EXTENT, helper) == 0);
    assert(s3ce_patch_context_menu(code, CODE_EXTENT - 1, code, CODE_EXTENT, helper) == 0);
    assert(s3ce_patch_context_menu(code, CODE_EXTENT, code + 4, CODE_EXTENT - 4, helper) == 0);
    assert(s3ce_patch_context_menu(code, CODE_EXTENT, code, CODE_EXTENT - 1, helper) == 0);
    assert(s3ce_patch_context_menu(code, CODE_EXTENT, code, CODE_EXTENT + 1, helper) == 0);
    assert(s3ce_patch_context_menu(code + 1, CODE_EXTENT, code + 1, CODE_EXTENT, helper) == 0);
    assert(s3ce_patch_context_menu(code, CODE_EXTENT, code, CODE_EXTENT, 0) == 0);
    assert(s3ce_patch_context_menu(code, CODE_EXTENT, code, CODE_EXTENT, helper & ~1u) == 0);
    const size_t spans[][2] = {
        {RENDER_HEAD, sizeof(render_head)}, {RENDER_TAIL, sizeof(render_tail)},
        {0xae458u, sizeof(display_y)}, {0x1494a0u, sizeof(convert_int)},
        {0x81bc4u, sizeof(set_bounds)}, {0x86338u, sizeof(render_return)}
    };
    for (size_t i = 0; i < sizeof(spans) / sizeof(spans[0]); ++i) {
        for (size_t j = 0; j < spans[i][1]; ++j) {
            size_t at = spans[i][0] + j;
            code[at] ^= 1;
            assert(s3ce_patch_context_menu(code, CODE_EXTENT, code, CODE_EXTENT, helper) == -1);
            code[at] ^= 1;
        }
    }
    assert(s3ce_patch_context_menu(code, CODE_EXTENT, code, CODE_EXTENT, helper) == 1);
    assert(s3ce_patch_context_menu(code, CODE_EXTENT, code, CODE_EXTENT, helper) == 2);
    assert(word_at((uintptr_t)code + 0x86328u) == (uintptr_t)code);
    assert(word_at((uintptr_t)code + 0x8632cu) == helper);
    assert(s3ce_patch_context_menu(code, CODE_EXTENT, code, CODE_EXTENT, helper + 2) == -1);
    assert(word_at((uintptr_t)code + 0x86328u) == (uintptr_t)code);
    assert(!memcmp(code + RENDER_HEAD, render_head, sizeof(render_head)));
    assert(!memcmp(code + 0x86338u, render_return, sizeof(render_return)));
    munmap(code, CODE_EXTENT);
    puts("Context menu patch: source tamper rejection, bounds, ABI thunk and idempotence passed");
    return 0;
}
