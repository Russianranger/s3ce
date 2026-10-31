#ifndef S3CE_CONTEXT_MENU_H
#define S3CE_CONTEXT_MENU_H
#include <stddef.h>
#include <stdint.h>

int s3ce_patch_context_menu(void *allocation, size_t allocation_length,
    const void *flush_start, uint32_t flush_length, uintptr_t thumb_helper);
void s3ce_context_menu_bounds(void *menu, uintptr_t game_base);
#endif
