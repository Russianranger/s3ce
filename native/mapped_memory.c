#include "mapped_memory.h"
#include <string.h>

int s3ce_parse_readable_memory(FILE *maps, struct s3ce_readable_memory *memory) {
    memory->count = 0;
    if (!maps) return 0;
    char line[512];
    while (fgets(line, sizeof(line), maps)) {
        unsigned long long first, last;
        char permissions[5];
        if (sscanf(line, "%16llx-%16llx %4s", &first, &last, permissions) != 3 ||
            permissions[0] != 'r' || first >= last || last > UINTPTR_MAX) continue;
        uintptr_t start = (uintptr_t)first, end = (uintptr_t)last;
        if (memory->count && memory->ranges[memory->count - 1].end >= start) {
            if (memory->ranges[memory->count - 1].end < end)
                memory->ranges[memory->count - 1].end = end;
        } else if (memory->count < sizeof(memory->ranges) / sizeof(memory->ranges[0])) {
            memory->ranges[memory->count].start = start;
            memory->ranges[memory->count++].end = end;
        }
    }
    return memory->count != 0;
}

int s3ce_load_readable_memory(struct s3ce_readable_memory *memory) {
    FILE *maps = fopen("/proc/self/maps", "r");
    int result = s3ce_parse_readable_memory(maps, memory);
    if (maps) fclose(maps);
    return result;
}

int s3ce_read_mapped_memory(void *context, uintptr_t address, void *out, size_t size) {
    const struct s3ce_readable_memory *memory = context;
    if (!memory || !out || !size) return 0;
    for (size_t i = 0; i < memory->count; ++i) {
        uintptr_t start = memory->ranges[i].start, end = memory->ranges[i].end;
        if (address >= start && address < end && size <= end - address) {
            memcpy(out, (const void *)address, size);
            return 1;
        }
    }
    return 0;
}
