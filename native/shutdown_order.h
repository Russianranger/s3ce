#ifndef S3CE_SHUTDOWN_ORDER_H
#define S3CE_SHUTDOWN_ORDER_H
#include <stddef.h>
#include <stdint.h>

int s3ce_patch_shutdown_order(void *allocation, size_t allocation_length,
    const void *flush_start, uint32_t flush_length, uintptr_t thumb_helper);
void s3ce_finish_shutdown(uintptr_t game_base);
#endif
