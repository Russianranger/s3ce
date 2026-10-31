#ifndef S3CE_MEMORY_COMPAT_H
#define S3CE_MEMORY_COMPAT_H
#include <stdint.h>
#include <stdio.h>
#include "graphics_diagnostics.h"
struct s3ce_memory_info {
    uint64_t total_kib;
    uint64_t free_kib;
    int total_bytes;
    int free_bytes;
    unsigned fields;
};
int s3ce_memory_kib_to_legacy_bytes(uint64_t kib);
void s3ce_parse_memory_info(FILE *input, struct s3ce_memory_info *info);
void s3ce_read_memory_info(const char *path, struct s3ce_memory_info *info);
/* ABI-compatible replacement for get_mem_info(int& total, int& free). */
void s3ce_get_memory_info(int *total, int *free_bytes, s3ce_graphics_log logger);
#endif
