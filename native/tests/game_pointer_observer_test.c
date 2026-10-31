#include "../game_pointer_observer.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { IMAGE_SIZE = 0x166ad8, DATA_SIZE = 0x20000, HEAP_SIZE = 0x6000 };
struct fixture {
    uintptr_t code, data, heap;
    unsigned char *image, *globals, *objects;
    unsigned calls, fail_call;
    int deny_menu_fields;
};

static int read_memory(void *context, uintptr_t address, void *out, size_t size) {
    struct fixture *f = context;
    ++f->calls;
    if (f->calls == f->fail_call) return 0;
    if (f->deny_menu_fields && address >= f->heap + 0x30a8 && address < f->heap + 0x4000)
        assert(!"Observer read menu-only fields from SceneGame/unknown Scene");
    struct { uintptr_t base; size_t size; unsigned char *bytes; } ranges[] = {
        {f->code, IMAGE_SIZE, f->image}, {f->data, DATA_SIZE, f->globals},
        {f->heap, HEAP_SIZE, f->objects}};
    for (size_t i = 0; i < sizeof(ranges) / sizeof(ranges[0]); ++i) {
        if (address >= ranges[i].base && address - ranges[i].base <= ranges[i].size
                && size <= ranges[i].size - (address - ranges[i].base)) {
            memcpy(out, ranges[i].bytes + address - ranges[i].base, size);
            return 1;
        }
    }
    return 0;
}

static void put(unsigned char *bytes, size_t offset, uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) bytes[offset + i] = (unsigned char)(value >> (i * 8));
}

static struct fixture make(uintptr_t code, uintptr_t data, uintptr_t heap) {
    struct fixture f = {code, data, heap, calloc(1, IMAGE_SIZE), calloc(1, DATA_SIZE),
                        calloc(1, HEAP_SIZE), 0, 0, 0};
    assert(f.image && f.globals && f.objects);
    memcpy(f.image + 0x3aeb4, "\x30\x40\x2d\xe9\x04\x20\x90\xe5", 8);
    memcpy(f.image + 0x3af84, "\x04\xe0\x2d\xe5\x00\x10\x90\xe5", 8);
    memcpy(f.image + 0xeddd4, "\x04\x00\x9f\xe5\x00\x00\x90\xe5", 8);
    for (unsigned i = 0; i < 3; ++i)
        put(f.image, ((unsigned[]){0x3af78, 0x3afdc, 0x11644c})[i], data + 0x54);
    put(f.image, 0x3af7c, data + 0x5c); put(f.image, 0x3afe0, data + 0x5c);
    put(f.image, 0xedde0, data + 0xfc);
    put(f.globals, 0xa0, heap); put(f.globals, 0xfc, heap);
    put(f.objects, 0, code + 0x15f690);
    put(f.objects, 0x330, 1); put(f.objects, 0x340, heap + 0x1000);
    put(f.objects, 0x1008, heap + 0x2000);
    put(f.objects, 0x2000, 3); put(f.objects, 0x2004, 0);
    put(f.objects, 0x40, heap + 0x3000);
    put(f.objects, 0x420, 0x12340001); put(f.objects, 0x430, 0x12340000);
    put(f.objects, 0x424, 0xffffff); put(f.objects, 0x428, UINT32_MAX); put(f.objects, 0x42c, 30303);
    put(f.objects, 0x3000, code + 0x15fb70);
    put(f.objects, 0x3084, 3); put(f.objects, 0x3090, 0);
    put(f.objects, 0x3098, 500); put(f.objects, 0x309c, 600);
    put(f.objects, 0x30a0, 900); put(f.objects, 0x30a4, 630);
    put(f.objects, 0x31ac, 13); put(f.objects, 0x3e20, 0xc0700000);  //-3.75f
    put(f.objects, 0x30f8, UINT32_MAX); put(f.objects, 0x31bc, 7);
    return f;
}

static void run(uintptr_t code, uintptr_t data, uintptr_t heap) {
    struct fixture f = make(code, data, heap);
    char out[512];
    assert(s3ce_observe_game_pointer(code, code + 0x3af84, read_memory, &f, out, sizeof(out)));
    unsigned total_reads = f.calls;
    for (const char **part = (const char *[]){"active=1 counts=3,0", "Scene=SceneMenu", "gesture=3 primary=0",
                                             "origin=500,600 current=900,630", "menuState=13",
                                             "engine420=1 engine430=0", "menuRoute=-1 menu1bc=7",
                                             "transition424=0x00ffffff direction428=-1 speed42c=30303",
                                             "angleBits=0xc0700000 angle=-3.75", NULL}; *part; ++part)
        assert(strstr(out, *part));
    assert(total_reads < 40);
    /* Every failed validated-read boundary must stop safely and explain why. */
    for (unsigned fail = 1; fail <= total_reads; ++fail) {
        f.calls = 0; f.fail_call = fail;
        assert(!s3ce_observe_game_pointer(code, code + 0x3aeb4, read_memory, &f, out, sizeof(out)));
        assert(strstr(out, "unavailable"));
    }
    f.fail_call = 0; f.calls = 0;
    f.deny_menu_fields = 1;
    put(f.objects, 0x3000, code + 0x15fac8);
    assert(s3ce_observe_game_pointer(code, code + 0x3af84, read_memory, &f, out, sizeof(out)));
    assert(strstr(out, "Scene=SceneGame") && !strstr(out, "angle"));
    put(f.objects, 0x3000, 0x12345678);
    assert(s3ce_observe_game_pointer(code, code + 0x3af84, read_memory, &f, out, sizeof(out)));
    assert(strstr(out, "Scene=other") && !strstr(out, "gesture="));
    f.deny_menu_fields = 0;
    put(f.objects, 0x40, 0);
    assert(s3ce_observe_game_pointer(code, code + 0x3af84, read_memory, &f, out, sizeof(out)));
    assert(strstr(out, "Scene=none"));
    put(f.objects, 0x40, heap + 0x3000);
    put(f.objects, 0x3000, code + 0x15fb70);
    put(f.objects, 0x2004, 51);
    assert(s3ce_observe_game_pointer(code, code + 0x3af84, read_memory, &f, out, sizeof(out)));
    assert(strstr(out, "INVALID_QUEUE"));
    f.calls = 0;
    assert(!s3ce_observe_game_pointer(code, code + 0x3af85, read_memory, &f, out, sizeof(out)));
    assert(f.calls == 0);
    assert(!s3ce_observe_game_pointer(UINT32_MAX - 0x100, 0, read_memory, &f, out, sizeof(out)));
    assert(f.calls == 0);
    f.image[0x3aeb4] ^= 1;
    assert(!s3ce_observe_game_pointer(code, code + 0x3af84, read_memory, &f, out, sizeof(out)));
    assert(strstr(out, "instruction guard"));
    f.image[0x3aeb4] ^= 1;
    put(f.image, 0xedde0, data + 0x100);  // Wrong layout; never follow this pointer.
    assert(!s3ce_observe_game_pointer(code, code + 0x3af84, read_memory, &f, out, sizeof(out)));
    assert(strstr(out, "split-data layout"));
    put(f.image, 0xedde0, data + 0xfc);
    /* The production proxy uses512 bytes: even the longest raw field values
     * must retain the final CAS angle rather than silently truncate it. */
    for (const unsigned *offset = (const unsigned[]){0x330, 0x420, 0x424, 0x42c, 0x430,
            0x2000, 0x2004, 0x3084, 0x3090, 0x31ac, 0x31bc, 0}; *offset; ++offset)
        put(f.objects, *offset, UINT32_MAX);
    for (const unsigned *offset = (const unsigned[]){0x428, 0x3098, 0x309c, 0x30a0, 0x30a4, 0x30f8, 0};
            *offset; ++offset) put(f.objects, *offset, 0x80000000);
    put(f.objects, 0x3e20, 0x7f7fffff);
    assert(s3ce_observe_game_pointer(code, code + 0x3af84, read_memory, &f, out, sizeof(out)));
    assert(strstr(out, "angleBits=0x7f7fffff angle="));
    assert(strlen(out) < sizeof(out) - 1);
    out[0] = 'x';
    assert(s3ce_observe_game_pointer(code, code + 0x3af84, read_memory, &f, out, 1));
    assert(out[0] == 0);
    assert(!s3ce_observe_game_pointer(code, code + 0x3af84, read_memory, &f, NULL, 0));
    free(f.image); free(f.globals); free(f.objects);
}

int main(void) {
    run(0x4a000000, 0x68000000, 0x60000000);
    run(0xc0cb8000, 0xe3000000, 0xd0000000);
    puts("PASS game observer: split code/data, high addresses, exact profile guards, all failed reads, Scene classes, bounds, and no direct runtime dereferences");
    return 0;
}
