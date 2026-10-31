#ifndef S3CE_HUD_INPUT_H
#define S3CE_HUD_INPUT_H
#include <stddef.h>
#include <stdint.h>
/* 0 unrelated span; -1 unknown/tampered code; 1 patched; 2 already patched. */
int s3ce_patch_hud_input(void *, size_t, const void *, uint32_t, uintptr_t);
void s3ce_hud_status_width_gateway(void);
#endif
