#include "image_pixels.h"
#include <string.h>

#define CODE_EXTENT 0x166ad8u
/* Original S3E SHA256: 8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a.
 * Immutable Image2D already owns a complete, bounded object-body byte array.
 * Its setter copies pixels synchronously into the image/mipmap allocations.
 * Borrow that body slice until the setter returns, avoiding a second staging
 * allocation. The dispatcher retains and frees the body at its original site.
 */
static const uint32_t dispatch[] = {
    0xe92d4ff0u, 0xe1a05000u, 0xe5900000u, 0xe1a07001u,
    0xe590102cu, 0xe24dd0a4u, 0xe1a08002u, 0xe1a00005u,
    0xe1a0e00fu, 0xe12fff11u, 0xe3700001u, 0xe1a04000u,
    0x028dd0a4u, 0x08bd4ff0u, 0x03a00000u, 0x012fff1eu,
    0xe1a00005u, 0xeb00581bu, 0xe1a01c20u, 0xe20028ffu,
    0xe1811422u, 0xe2002cffu, 0xe1811402u, 0xe1816c00u,
    0xe1a00006u, 0xeb025cabu, 0xe1a01000u, 0xe58d009cu,
    0xe1a02006u, 0xe1a00005u, 0xeb005924u, 0xe3a00020u,
    0xeb025ca6u, 0xe59d109cu, 0xe1a02006u, 0xeb005dffu,
    0xe1a01000u, 0xe28d008cu, 0xeb00598cu, 0xe3540017u,
    0xe3a0a000u, 0x379ff104u,
};
static const uint32_t immutable[] = {
    0xe3540000u, 0x1a000491u, 0xe28d0078u, 0xeb006c24u,
    0xe59f9a30u, 0xe3a0b000u, 0xe580b008u, 0xe480900cu,
    0xe580b000u,
};
static const uint32_t pixels[] = {
    0xe28d008cu, 0xeb005576u, 0xe1a01c20u, 0xe20028ffu,
    0xe1811422u, 0xe2002cffu, 0xe1811402u, 0xe1815c00u,
    0xe1a00005u, 0xeb025a06u, 0xe1a04000u, 0xe1a01000u,
    0xe1a02005u, 0xe28d008cu, 0xeb00567fu, 0xe59d0084u,
    0xe3500000u, 0x15900008u, 0x01a0000bu, 0xe150000bu,
    0x0a000004u, 0xe1a02004u, 0xe28d1078u, 0xe1a0000au,
    0xeb003263u, 0xea000002u, 0xe1a01004u, 0xe1a0000au,
    0xeb002ff2u, 0xe1a00004u, 0xeb0259edu,
};
static const uint32_t palette_cleanup[] = {
    0xe28d5078u, 0xe59d4080u, 0xe1a00005u, 0xe58d9078u,
    0xeb004b5cu, 0xe1b01000u, 0x0a000009u, 0xe3540000u,
    0xe3a00000u, 0xda000004u, 0xe2800001u, 0xe1500004u,
    0xbafffffcu, 0xe3510000u, 0x0a000001u, 0xe1a00001u,
    0xeb0264fbu, 0xe1a00005u, 0xeb006ba4u, 0xea000401u,
};
static const uint32_t owner_cleanup[] = {
    0xe59d009cu, 0xeb02554bu, 0xe28d008cu, 0xeb005267u,
    0xe28dd0a4u, 0xe8bd4ff0u, 0xe3a00001u, 0xe12fff1eu,
};
static const uint32_t stream_constructor[] = {
    0xe92d4070u, 0xe1a05001u, 0xe1a04002u, 0xebfff72au,
    0xe59f1024u, 0xe5801000u, 0xe3a01000u, 0xe5801010u,
    0xe580400cu, 0xe5805008u, 0xe5801018u, 0xe5804014u,
    0xe580101cu, 0xe8bd4070u, 0xe12fff1eu,
};
static const uint32_t stream_read[] = {
    0xe92d4070u, 0xe1a04000u, 0xe1a00001u, 0xe5941014u,
    0xe594301cu, 0xe1a05002u, 0xe0411003u, 0xe1510002u,
    0xb1a05001u, 0xe5941010u, 0xe5942008u, 0xe0811003u,
    0xe0811002u, 0xe1a02005u, 0xebfd36ddu, 0xe594001cu,
    0xe0800005u, 0xe584001cu, 0xe1a00005u, 0xe8bd4070u,
    0xe12fff1eu,
};
struct fingerprint { uint32_t offset; const void *bytes; size_t length; };
static const struct fingerprint profile[] = {
    {0x9b98cu, dispatch, sizeof(dispatch)},
    {0x9c2e4u, immutable, sizeof(immutable)},
    {0x9c460u, pixels, sizeof(pixels)},
    {0x9c4dcu, palette_cleanup, sizeof(palette_cleanup)},
    {0x9d75cu, owner_cleanup, sizeof(owner_cleanup)},
    {0xb321cu, stream_constructor, sizeof(stream_constructor)},
    {0xb3108u, stream_read, sizeof(stream_read)},
};

static s3ce_graphics_log image_log;
static unsigned small_logs, large_logs, error_logs;

static uint32_t word_at(uintptr_t address) {
    uint32_t value;
    memcpy(&value, (const void *)address, sizeof(value));
    return value;
}
static void store_word(uintptr_t address, uint32_t value) {
    memcpy((void *)address, &value, sizeof(value));
}

/* The caller is the pinned dispatcher's stack frame, never arbitrary user
 * memory. Fields are those of its exact raw ByteArrayInputStream constructor.
 * after_read selects the same slice after the original ReadFully cursor step.
 * In particular, equality to the owned allocation excludes a borrowed pointer
 * being passed to the original array delete, without global ownership state.
 */
int s3ce_image_pixels_view(uintptr_t frame, uintptr_t base, uint32_t count,
                          int after_read, uintptr_t *pixels_out) {
    if (!frame || (frame & 3u) || frame > UINTPTR_MAX - 0xa0u ||
        !base || base > UINT32_MAX - CODE_EXTENT || !pixels_out) return 0;
    uintptr_t body = word_at(frame + 0x9cu);
    uintptr_t stream = word_at(frame + 0x94u);
    if (!body || !stream || (stream & 3u) || stream > UINT32_MAX - 0x20u ||
        word_at(stream) != base + 0x1614b0u ||
        word_at(stream + 8u) != body || word_at(stream + 0x10u) != 0) return 0;
    uint32_t length = word_at(stream + 0x14u);
    uint32_t cursor = word_at(stream + 0x1cu);
    if (word_at(stream + 0xcu) != length || cursor > length ||
        body > UINT32_MAX - length) return 0;
    if (after_read) {
        if (count > cursor) return 0;
        cursor -= count;
    } else if (count > length - cursor) return 0;
    *pixels_out = body + cursor;
    return 1;
}

/* Only a malformed Image2D body reaches this path. Use the same original
 * deleting destructor, palette-vector detach/free, owned-body delete and
 * DataInputStream destructor as the normal dispatcher. Nothing is published
 * in its object vectors; the gateway then returns false from that dispatcher.
 */
static void reject_image(uintptr_t frame, uintptr_t base, void *image) {
    void (*destroy_image)(void *) = (void *)(base + 0xa9548u);
    void *(*detach_palette)(void *) = (void *)(base + 0xaf264u);
    void (*free_palette)(void *) = (void *)(base + 0x135910u);
    void (*destroy_palette)(void *) = (void *)(base + 0xb73bcu);
    void (*delete_body)(void *) = (void *)(base + 0x132c94u);
    void (*destroy_stream)(void *) = (void *)(base + 0xb210cu);
    destroy_image(image);
    store_word(frame + 0x78u, (uint32_t)(base + 0x16205cu));
    void *detached = detach_palette((void *)(frame + 0x78u));
    if (detached) free_palette(detached);
    destroy_palette((void *)(frame + 0x78u));
    delete_body((void *)(uintptr_t)word_at(frame + 0x9cu));
    destroy_stream((void *)(frame + 0x8cu));
}

void *s3ce_image_pixels_borrow(uintptr_t frame, uintptr_t base, void *image,
                              uint32_t count) {
    uintptr_t pixels;
    if (!s3ce_image_pixels_view(frame, base, count, 0, &pixels)) {
        if (image_log && __atomic_fetch_add(&error_logs, 1, __ATOMIC_RELAXED) < 8)
            image_log(6, "Image2D pixel body rejected: bytes=%u; parser returns false", count);
        reject_image(frame, base, image);
        return NULL;
    }
    uintptr_t stream = word_at(frame + 0x94u);
    uint32_t cursor = word_at(stream + 0x1cu);
    store_word(stream + 0x1cu, cursor + count);
    unsigned *counter = count >= 768u * 1024u ? &large_logs : &small_logs;
    if (image_log && __atomic_fetch_add(counter, 1, __ATOMIC_RELAXED) < 64)
        image_log(4, "Image2D borrowed pixels: format=%u %ux%u bytes=%u cursor=%u; staging allocation avoided",
            word_at((uintptr_t)image + 0x2cu), word_at((uintptr_t)image + 0x30u),
            word_at((uintptr_t)image + 0x34u), count, cursor);
    return (void *)pixels;
}

void s3ce_image_pixels_release(uintptr_t frame, uintptr_t base, void *pixels,
                              uint32_t count) {
    uintptr_t borrowed;
    if (s3ce_image_pixels_view(frame, base, count, 1, &borrowed) &&
        (uintptr_t)pixels == borrowed) return;
    /* This is the original Image2D staging-delete call site only. Retain its
     * delete behavior for a pointer that is not the canonical borrowed slice. */
    void (*delete_pixels)(void *) = (void *)(base + 0x132c94u);
    delete_pixels(pixels);
}

#if defined(__arm__)
/* LR=game+9c488. Preserve the dispatcher's callee-saved values and 8-byte
 * stack alignment. A rejected body has already released every local owner;
 * return false through the dispatcher's own original saved-register frame. */
__attribute__((naked)) void s3ce_image_pixels_borrow_gateway(void) {
    __asm__ volatile(
        "push {r1-r5, lr}\n"
        "add r0, sp, #24\n"
        "movw r2, #0xc488\n"
        "movt r2, #9\n"
        "sub r1, lr, r2\n"
        "mov r2, r10\n"
        "mov r3, r5\n"
        "bl s3ce_image_pixels_borrow\n"
        "pop {r1-r5, lr}\n"
        "cmp r0, #0\n"
        "beq 1f\n"
        "mov r4, r0\n"
        "add lr, lr, #4\n"
        "bx lr\n"
        "1: add sp, sp, #0xa4\n"
        "pop {r4-r11, lr}\n"
        "mov r0, #0\n"
        "bx lr\n");
}
/* LR=game+9c4dc. This hook executes only after the synchronous pixel setter. */
__attribute__((naked)) void s3ce_image_pixels_release_gateway(void) {
    __asm__ volatile(
        "push {r0-r3, r12, lr}\n"
        "add r0, sp, #24\n"
        "movw r2, #0xc4dc\n"
        "movt r2, #9\n"
        "sub r1, lr, r2\n"
        "mov r2, r4\n"
        "mov r3, r5\n"
        "bl s3ce_image_pixels_release\n"
        "pop {r0-r3, r12, lr}\n"
        "bx lr\n");
}
#else
void s3ce_image_pixels_borrow_gateway(void) {}
void s3ce_image_pixels_release_gateway(void) {}
#endif

struct correction { uint32_t offset, before, after; };
int s3ce_patch_image_pixels(void *allocation, size_t allocation_length,
    const void *flush_start, uint32_t flush_length, uintptr_t borrow_gateway,
    uintptr_t release_gateway, s3ce_graphics_log logger) {
    uintptr_t base = (uintptr_t)allocation;
    if (!base || flush_start != allocation || (base & 3u) ||
        allocation_length < CODE_EXTENT || flush_length < CODE_EXTENT ||
        flush_length > allocation_length || base > UINTPTR_MAX - allocation_length ||
        !borrow_gateway || !(borrow_gateway & 1u) || borrow_gateway > UINT32_MAX ||
        !release_gateway || !(release_gateway & 1u) || release_gateway > UINT32_MAX) return 0;
    struct correction changes[] = {
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
    unsigned char *code = allocation;
    unsigned changed = 0;
    for (size_t i=0; i<sizeof(changes)/sizeof(changes[0]); ++i) {
        uint32_t actual = word_at(base + changes[i].offset);
        if (actual == changes[i].after) ++changed;
        else if (actual != changes[i].before) return -1;
    }
    if (changed && changed != sizeof(changes)/sizeof(changes[0])) return -1;
    for (size_t i=0; i<sizeof(profile)/sizeof(profile[0]); ++i)
        for (size_t j=0; j<profile[i].length; j+=4) {
            uint32_t expected = word_at((uintptr_t)profile[i].bytes + j);
            if (changed) for (size_t k=0; k<sizeof(changes)/sizeof(changes[0]); ++k)
                if (profile[i].offset+j == changes[k].offset) expected = changes[k].after;
            if (word_at(base+profile[i].offset+j) != expected) return -1;
        }
    image_log = logger;
    if (changed) return 2;
    /* The code-allocation lock is held by our caller, which flushes the entire
     * executable allocation after this all-or-nothing fingerprint check. */
    for (size_t i=0; i<sizeof(changes)/sizeof(changes[0]); ++i)
        memcpy(code+changes[i].offset, &changes[i].after, 4);
    return 1;
}
