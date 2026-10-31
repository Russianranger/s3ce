#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include "../memory_compat.c"

static struct s3ce_memory_info parse(const char *text) {
    FILE *input = tmpfile();
    assert(input);
    assert(fputs(text, input) >= 0);
    rewind(input);
    struct s3ce_memory_info result;
    s3ce_parse_memory_info(input, &result);
    fclose(input);
    return result;
}
int main(void) {
    assert(s3ce_memory_kib_to_legacy_bytes(0) == 0);
    assert(s3ce_memory_kib_to_legacy_bytes(32) == 32768);
    assert(s3ce_memory_kib_to_legacy_bytes(64) == 65536);
    assert(s3ce_memory_kib_to_legacy_bytes(1048576) == 1073741824);
    assert(s3ce_memory_kib_to_legacy_bytes(2097151) == 2147482624);
    const uint64_t large[] = {2097152,3145728,4194304,5242880,7340032,16777216,UINT64_MAX};
    for (unsigned i = 0; i < sizeof(large)/sizeof(large[0]); ++i)
        assert(s3ce_memory_kib_to_legacy_bytes(large[i]) == INT32_MAX);
    struct s3ce_memory_info info = parse("MemTotal: 16777216 kB\nMemAvailable: 99 kB\nMemFree: 3145728 kB\n");
    assert(info.fields == 3 && info.total_kib == 16777216 && info.free_kib == 3145728);
    assert(info.total_bytes == INT32_MAX && info.free_bytes == INT32_MAX);
    info = parse("MemTotal: 16777216 kB\nMemFree: 32 kB\n");
    assert(info.fields == 3 && info.free_bytes == 32768 && info.free_bytes < 65536);
    info = parse("MemTotal: 16777216 kB\nMemFree: 0 kB\n");
    assert(info.fields == 3 && info.free_bytes == 0); /* Real zero remains low memory. */
    info = parse("MemTotal: 1024 kB\nMemFree: -1 kB\nMemAvailable: 99999999 kB\n");
    assert(info.fields == 1 && info.total_bytes == 1048576 && info.free_bytes == -1);
    info = parse("MemFree: 18446744073709551616 kB\nMemTotal: 512 bytes\n");
    assert(info.fields == 0 && info.total_bytes == -1 && info.free_bytes == -1);
    info = parse("MemTotal: 18446744073709551615 kB\nMemFree: 4096 kB trailing-garbage\n");
    assert(info.fields == 1 && info.total_bytes == INT32_MAX && info.free_bytes == -1);
    s3ce_parse_memory_info(NULL, &info);
    assert(info.fields == 0 && info.total_bytes == -1 && info.free_bytes == -1);
    s3ce_read_memory_info("/s3ce-test/nonexistent-proc-file", &info);
    assert(info.fields == 0 && info.total_bytes == -1 && info.free_bytes == -1);
    puts("64-bit MemFree/MemTotal parsing, legacy-int saturation and genuine low-RAM preservation: PASS");
}
