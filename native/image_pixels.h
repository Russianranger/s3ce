#ifndef S3CE_IMAGE_PIXELS_H
#define S3CE_IMAGE_PIXELS_H
#include <stddef.h>
#include <stdint.h>
#include "graphics_diagnostics.h"

int s3ce_patch_image_pixels(void *, size_t, const void *, uint32_t,
    uintptr_t, uintptr_t, s3ce_graphics_log);
int s3ce_image_pixels_view(uintptr_t, uintptr_t, uint32_t, int, uintptr_t *);
void *s3ce_image_pixels_borrow(uintptr_t, uintptr_t, void *, uint32_t);
void s3ce_image_pixels_release(uintptr_t, uintptr_t, void *, uint32_t);
void s3ce_image_pixels_borrow_gateway(void);
void s3ce_image_pixels_release_gateway(void);
#endif
