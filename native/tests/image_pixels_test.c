#define _GNU_SOURCE
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "../image_pixels.c"

static void view_tests(void) {
    const size_t length = 0x4000;
    unsigned char *memory = mmap(NULL, length, PROT_READ | PROT_WRITE,
        MAP_PRIVATE | MAP_ANONYMOUS | MAP_32BIT, -1, 0);
    assert(memory != MAP_FAILED && (uintptr_t)memory <= UINT32_MAX - length);
    uintptr_t frame = (uintptr_t)memory, body = frame + 0x1000;
    uintptr_t stream = frame + 0x2000, base = 0xc3014000u, output;
    const uintptr_t untouched = 0x13579bdfu;
#define FRAME(offset, value) store_word(frame + (offset), (uint32_t)(value))
#define STREAM(offset, value) store_word(stream + (offset), (uint32_t)(value))
#define RESET() do { \
    memset(memory, 0, length); \
    FRAME(0x9c, body); FRAME(0x94, stream); \
    STREAM(0, base + 0x1614b0u); STREAM(8, body); \
    STREAM(0xc, 256); STREAM(0x10, 0); \
    STREAM(0x14, 256); STREAM(0x1c, 30); \
} while (0)
#define EXPECT(count, after, expected) do { \
    output = untouched; \
    assert(s3ce_image_pixels_view(frame, base, (count), (after), &output) == 1); \
    assert(output == (expected)); \
} while (0)
#define REFUSE(count, after) do { \
    output = untouched; \
    assert(s3ce_image_pixels_view(frame, base, (count), (after), &output) == 0); \
    assert(output == untouched); \
} while (0)
    RESET();
    EXPECT(20, 0, body + 30);
    assert(word_at(stream + 0x1c) == 30); /* A view never advances the cursor. */
    EXPECT(30, 1, body);
    EXPECT(0, 0, body + 30);
    EXPECT(0, 1, body + 30);
    REFUSE(31, 1);
    REFUSE(227, 0);
    REFUSE(UINT32_MAX, 0);
    REFUSE(UINT32_MAX, 1);
    STREAM(0x1c, 50);
    EXPECT(20, 1, body + 30);
    STREAM(0x1c, 256);
    EXPECT(0, 0, body + 256);
    EXPECT(0, 1, body + 256);
    EXPECT(256, 1, body);
    REFUSE(1, 0);
    STREAM(0x1c, 257);
    REFUSE(0, 0);
    REFUSE(0, 1);
    RESET(); STREAM(0x14, 0); STREAM(0xc, 0); STREAM(0x1c, 0);
    EXPECT(0, 0, body);
    EXPECT(0, 1, body);
    REFUSE(1, 0);
    REFUSE(1, 1);

    RESET(); FRAME(0x9c, 0); REFUSE(1, 0);
    RESET(); FRAME(0x94, 0); REFUSE(1, 0);
    RESET(); FRAME(0x94, stream + 1); REFUSE(1, 0);
    RESET(); FRAME(0x94, UINT32_MAX & ~3u); REFUSE(1, 0);
    RESET(); STREAM(0, base + 0x1614b4u); REFUSE(1, 0);
    RESET(); STREAM(8, body + 4); REFUSE(1, 0);
    RESET(); STREAM(0x10, 4); REFUSE(1, 0);
    RESET(); STREAM(0xc, 255); REFUSE(1, 0);
    RESET(); STREAM(0xc, 257); REFUSE(1, 1);
    /* The body is only compared, never dereferenced by the view. Exercise
     * the precise ARM32 address arithmetic limits without mapping that end. */
    RESET(); FRAME(0x9c, UINT32_MAX - 256u);
    STREAM(8, UINT32_MAX - 256u); STREAM(0x1c, 256);
    EXPECT(0, 0, UINT32_MAX);
    EXPECT(256, 1, UINT32_MAX - 256u);
    FRAME(0x9c, UINT32_MAX - 255u); STREAM(8, UINT32_MAX - 255u);
    REFUSE(0, 0);
    REFUSE(0, 1);
    RESET(); STREAM(0xc, UINT32_MAX); STREAM(0x14, UINT32_MAX);
    REFUSE(0, 0);

    RESET(); output = untouched;
    assert(!s3ce_image_pixels_view(0, base, 1, 0, &output));
    assert(!s3ce_image_pixels_view(frame + 1, base, 1, 0, &output));
    assert(!s3ce_image_pixels_view(UINTPTR_MAX & ~(uintptr_t)3,
        base, 1, 0, &output));
    assert(!s3ce_image_pixels_view(frame, 0, 1, 0, &output));
    assert(!s3ce_image_pixels_view(frame, (uintptr_t)UINT32_MAX - CODE_EXTENT + 1,
        1, 0, &output));
    assert(!s3ce_image_pixels_view(frame, base, 1, 0, NULL));
    assert(output == untouched);
    assert(munmap(memory, length) == 0);
#undef FRAME
#undef STREAM
#undef RESET
#undef EXPECT
#undef REFUSE
}

static void patch_tests(void) {
    const size_t length = 0x169000;
    const uintptr_t borrow_gateway = 0x21000001u, release_gateway = 0xdb000001u;
    const struct correction changes[] = {
        {0x9c480u, 0xe1a00005u, 0xe59fc000u},
        {0x9c484u, 0xeb025a06u, 0xe12fff3cu},
        {0x9c488u, 0xe1a04000u, (uint32_t)borrow_gateway},
        {0x9c48cu, 0xe1a01000u, 0xea000002u},
        {0x9c490u, 0xe1a02005u, (uint32_t)release_gateway},
        {0x9c494u, 0xe28d008cu, 0xe1a00000u},
        {0x9c498u, 0xeb00567fu, 0xe1a00000u},
        {0x9c4d4u, 0xe1a00004u, 0xe51fc04cu},
        {0x9c4d8u, 0xeb0259edu, 0xe12fff3cu},
    };
    unsigned char *code = malloc(length), *before = malloc(length);
    assert(code && before);
    memset(code, 0xa5, length);
    for (size_t i = 0; i < sizeof(profile) / sizeof(profile[0]); ++i)
        memcpy(code + profile[i].offset, profile[i].bytes, profile[i].length);
    memcpy(before, code, length);
#define PATCH(address, size, flush, span, borrow, release) \
    s3ce_patch_image_pixels((address), (size), (flush), (span), (borrow), (release), NULL)
    assert(PATCH(NULL, length, NULL, CODE_EXTENT, borrow_gateway, release_gateway) == 0);
    assert(PATCH(code, CODE_EXTENT - 1, code, CODE_EXTENT - 1,
        borrow_gateway, release_gateway) == 0);
    assert(PATCH(code, length, code + 4, CODE_EXTENT, borrow_gateway, release_gateway) == 0);
    assert(PATCH(code, length, code, CODE_EXTENT - 1, borrow_gateway, release_gateway) == 0);
    assert(PATCH(code, length, code, length + 1, borrow_gateway, release_gateway) == 0);
    assert(PATCH(code + 1, length - 1, code + 1, CODE_EXTENT,
        borrow_gateway, release_gateway) == 0);
    void *overflow = (void *)(UINTPTR_MAX & ~(uintptr_t)3);
    assert(PATCH(overflow, length, overflow, CODE_EXTENT, borrow_gateway, release_gateway) == 0);
    for (unsigned which = 0; which < 2; ++which) {
        uintptr_t b = which ? borrow_gateway : 0;
        uintptr_t r = which ? 0 : release_gateway;
        assert(PATCH(code, length, code, CODE_EXTENT, b, r) == 0);
        b = which ? borrow_gateway : borrow_gateway - 1;
        r = which ? release_gateway - 1 : release_gateway;
        assert(PATCH(code, length, code, CODE_EXTENT, b, r) == 0);
#if UINTPTR_MAX > UINT32_MAX
        b = which ? borrow_gateway : (uintptr_t)UINT32_MAX + 2;
        r = which ? (uintptr_t)UINT32_MAX + 2 : release_gateway;
        assert(PATCH(code, length, code, CODE_EXTENT, b, r) == 0);
#endif
    }
    assert(!memcmp(code, before, length));
    /* Every instruction byte in every pinned span must be checked before any
     * code write, including the original owner cleanup and stream constructor. */
    for (size_t i = 0; i < sizeof(profile) / sizeof(profile[0]); ++i)
        for (size_t j = 0; j < profile[i].length; ++j) {
            code[profile[i].offset + j] ^= 1;
            assert(PATCH(code, length, code, CODE_EXTENT, borrow_gateway, release_gateway) == -1);
            code[profile[i].offset + j] ^= 1;
        }
    assert(!memcmp(code, before, length));
    for (size_t i = 0; i < sizeof(changes) / sizeof(changes[0]); ++i) {
        memcpy(code + changes[i].offset, &changes[i].after, 4);
        assert(PATCH(code, length, code, CODE_EXTENT, borrow_gateway, release_gateway) == -1);
        memcpy(code, before, length);
    }
    assert(PATCH(code, length, code, CODE_EXTENT, borrow_gateway, release_gateway) == 1);
    for (size_t i = 0; i < sizeof(changes) / sizeof(changes[0]); ++i)
        memcpy(before + changes[i].offset, &changes[i].after, 4);
    assert(!memcmp(code, before, length));
    assert(PATCH(code, length, code, CODE_EXTENT, borrow_gateway, release_gateway) == 2);
    assert(PATCH(code, length, code, CODE_EXTENT, borrow_gateway + 4, release_gateway) == -1);
    assert(PATCH(code, length, code, CODE_EXTENT, borrow_gateway, release_gateway + 4) == -1);
    for (size_t i = 0; i < sizeof(changes) / sizeof(changes[0]); ++i) {
        for (size_t j = 0; j < 4; ++j) {
            code[changes[i].offset + j] ^= 1;
            assert(PATCH(code, length, code, CODE_EXTENT, borrow_gateway, release_gateway) == -1);
            code[changes[i].offset + j] ^= 1;
        }
        memcpy(code + changes[i].offset, &changes[i].before, 4);
        assert(PATCH(code, length, code, CODE_EXTENT, borrow_gateway, release_gateway) == -1);
        memcpy(code, before, length);
    }
    assert(!memcmp(code, before, length));
    free(code);
    free(before);
#undef PATCH
}

int main(void) {
    view_tests();
    patch_tests();
    puts("Image2D pixel views and patch guards: body/class/cursor/count limits, atomic fingerprint refusal and idempotence PASS");
    return 0;
}
