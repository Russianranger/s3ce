#include "code_flush.h"

int s3ce_flush_code_span(void *start, uint32_t length, void *allocation,
                          size_t allocation_length,
                          int (*platform_flush)(void *, uint32_t)) {
    if (!platform_flush) return -1;
    uintptr_t address = (uintptr_t)start;
    uintptr_t base = (uintptr_t)allocation;
    if (base && allocation_length && allocation_length <= UINT32_MAX &&
        allocation_length <= UINTPTR_MAX - base && address >= base &&
        address < base + allocation_length && length <= base + allocation_length - address) {
        start = allocation;
        length = (uint32_t)allocation_length;
    }
    return platform_flush(start, length);
}
