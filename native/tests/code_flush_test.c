#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "../code_flush.c"

static uintptr_t seen_start, seen_end, protected_start, protected_end;
static unsigned calls;
static int platform_result;
static int original_platform(void *start, uint32_t length) {
    ++calls;
    seen_start = (uintptr_t)start;
    seen_end = seen_start + length;
    /* Same ranges as the supplied 0x41020 mprotect+cacheflush routine. */
    protected_start = seen_start & ~(uintptr_t)4095;
    protected_end = seen_end;
    return platform_result;
}
int main(void) {
    const uintptr_t base = 0x50000000;
    const size_t code_extent = 0x166ad8;
    const size_t arena_end = code_extent + 508*16 + 1024;
    const size_t allocation = 0x169000;
    assert(arena_end <= allocation && arena_end > 0x167000);
    assert(s3ce_flush_code_span((void *)base, 0x167000, (void *)base, allocation, original_platform) == 0);
    assert(seen_start == base && seen_end == base+allocation);
    assert(protected_start <= base && protected_end >= base+arena_end);
    assert(seen_end >= base+arena_end); /* Every initial import/callback veneer is covered. */
    assert(s3ce_flush_code_span((void *)(base+0x168000), 1024, (void *)base, allocation, original_platform) == 0);
    assert(seen_start == base && seen_end == base+allocation);
    platform_result = -23;
    assert(s3ce_flush_code_span((void *)0x60000003, 17, (void *)base, allocation, original_platform) == -23);
    assert(seen_start == 0x60000003 && seen_end == 0x60000014); /* Unknown ranges unchanged. */
    assert(s3ce_flush_code_span((void *)(base+allocation-8), 32, (void *)base, allocation, original_platform) == -23);
    assert(seen_start == base+allocation-8 && seen_end == base+allocation+24);
    unsigned before = calls;
    assert(s3ce_flush_code_span((void *)base, 1, (void *)base, allocation, NULL) == -1 && calls == before);
    puts("Full generated-veneer allocation mprotect/cache range and original return semantics: PASS");
}
