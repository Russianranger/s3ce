#ifndef S3CE_MAPPED_MEMORY_H
#define S3CE_MAPPED_MEMORY_H
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
struct s3ce_readable_memory {
    struct { uintptr_t start, end; } ranges[512];
    size_t count;
};
int s3ce_parse_readable_memory(FILE *maps, struct s3ce_readable_memory *memory);
int s3ce_load_readable_memory(struct s3ce_readable_memory *memory);
/* This range check complements the source-proven same-engine-thread lifetime:
 * caller must only inspect objects that cannot be freed during observation. */
int s3ce_read_mapped_memory(void *context, uintptr_t address, void *out, size_t size);
#endif
