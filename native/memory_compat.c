#include "memory_compat.h"
#include <android/log.h>
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

int s3ce_memory_kib_to_legacy_bytes(uint64_t kib) {
    if (kib > (uint64_t)INT32_MAX / 1024) return INT32_MAX;
    return (int)(kib * 1024);
}

static int read_kib(const char *line, const char *key, uint64_t *result) {
    size_t length = strlen(key);
    if (strncmp(line, key, length)) return 0;
    const char *number = line + length;
    while (isspace((unsigned char)*number)) ++number;
    if (*number < '0' || *number > '9') return 0;
    errno = 0;
    char *end;
    unsigned long long value = strtoull(number, &end, 10);
    if (errno == ERANGE || end == number) return 0;
    while (*end == ' ' || *end == '\t') ++end;
    if (end[0] != 'k' || end[1] != 'B') return 0;
    end += 2;
    while (isspace((unsigned char)*end)) ++end;
    if (*end) return 0;
    *result = (uint64_t)value;
    return 1;
}

void s3ce_parse_memory_info(FILE *input, struct s3ce_memory_info *info) {
    *info = (struct s3ce_memory_info){.total_bytes = -1, .free_bytes = -1};
    if (!input) return;
    char line[512];
    while (fgets(line, sizeof(line), input)) {
        uint64_t value;
        if (read_kib(line, "MemTotal:", &value)) {
            info->total_kib = value;
            info->total_bytes = s3ce_memory_kib_to_legacy_bytes(value);
            info->fields |= 1;
        } else if (read_kib(line, "MemFree:", &value)) {
            info->free_kib = value;
            info->free_bytes = s3ce_memory_kib_to_legacy_bytes(value);
            info->fields |= 2;
        }
        if (info->fields == 3) break;
    }
}

void s3ce_read_memory_info(const char *path, struct s3ce_memory_info *info) {
    FILE *input = fopen(path, "r");
    s3ce_parse_memory_info(input, info);
    if (input) fclose(input);
}

void s3ce_get_memory_info(int *total, int *free_bytes, s3ce_graphics_log logger) {
    struct s3ce_memory_info info;
    s3ce_read_memory_info("/proc/meminfo", &info);
    if (total) *total = info.total_bytes;
    if (free_bytes) *free_bytes = info.free_bytes;
    static unsigned logged;
    if (__atomic_fetch_add(&logged, 1, __ATOMIC_RELAXED) < 8 && logger)
        logger(ANDROID_LOG_INFO,
            "Legacy RAM: fields=%u totalKiB=%llu freeKiB=%llu totalBytes=%d freeBytes=%d (signed-int saturation)",
            info.fields, (unsigned long long)info.total_kib, (unsigned long long)info.free_kib,
            info.total_bytes, info.free_bytes);
}
