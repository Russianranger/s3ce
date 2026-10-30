/* S3CE C interface to the MIT-licensed PowerVR software decoder. */
#ifndef S3CE_PVRTC_BRIDGE_H
#define S3CE_PVRTC_BRIDGE_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Decodes one PVRTC1 mip level to RGBA8888. Return 0 on success, -1 for an
 * invalid extent/buffer, -2 on allocation or decoding failure. RGB-only callers
 * must set decoded alpha bytes to 255 before upload. */
int s3ce_pvrtc_decode(const void *data, size_t data_size,
                     unsigned bits_per_pixel, unsigned width, unsigned height,
                     void *rgba, size_t rgba_size);
#ifdef __cplusplus
}
#endif
#endif
