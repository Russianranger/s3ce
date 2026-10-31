#include "../mapped_memory.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    struct s3ce_readable_memory memory;
    FILE *input = tmpfile();
    assert(input);
    fputs("00001000-00002000 r--p 00000000 00:00 0\n"
          "00002000-00003000 rw-p 00000000 00:00 0\n"
          "00003000-00004000 ---p 00000000 00:00 0\n"
          "00004000-00005000 r-xp 00000000 00:00 0\n"
          "malformed line\n", input);
    rewind(input);
    assert(s3ce_parse_readable_memory(input, &memory));
    assert(memory.count == 2);
    assert(memory.ranges[0].start == 0x1000 && memory.ranges[0].end == 0x3000);
    assert(memory.ranges[1].start == 0x4000 && memory.ranges[1].end == 0x5000);
    fclose(input);
    assert(!s3ce_parse_readable_memory(NULL, &memory) && memory.count == 0);
    unsigned char source[8] = {0,1,2,3,4,5,6,7}, output[8];
    memory.count = 1;
    memory.ranges[0].start = (uintptr_t)source;
    memory.ranges[0].end = (uintptr_t)source + sizeof(source);
    assert(s3ce_read_mapped_memory(&memory, (uintptr_t)source, output, 8));
    assert(!memcmp(source, output, 8));
    assert(s3ce_read_mapped_memory(&memory, (uintptr_t)source + 7, output, 1));
    assert(output[0] == 7);
    assert(!s3ce_read_mapped_memory(&memory, (uintptr_t)source + 7, output, 2));
    assert(!s3ce_read_mapped_memory(&memory, (uintptr_t)source + 8, output, 1));
    assert(!s3ce_read_mapped_memory(&memory, (uintptr_t)source - 1, output, 1));
    assert(!s3ce_read_mapped_memory(&memory, UINTPTR_MAX, output, 8));
    assert(!s3ce_read_mapped_memory(NULL, 0, output, 1));
    assert(!s3ce_read_mapped_memory(&memory, (uintptr_t)source, NULL, 1));
    assert(!s3ce_read_mapped_memory(&memory, (uintptr_t)source, output, 0));
    assert(s3ce_load_readable_memory(&memory));
    assert(s3ce_read_mapped_memory(&memory, (uintptr_t)source, output, 8));
    assert(!memcmp(source, output, 8));
    assert(!s3ce_read_mapped_memory(&memory, 0, output, 8));
    puts("PASS readable-map snapshots merge adjacent regions, reject gaps/overflow, and bound real self-memory reads");
}
