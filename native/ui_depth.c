#include "ui_depth.h"
#include <string.h>

#define GAME_CODE_EXTENT 0x166ad8u
#define PROJECTION_LOAD 0x135d50u
#define Z_ARGUMENT 0x30u

/* Exact source S3E SHA256:
 * 8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a.
 * No relocated literals are inside this 29-instruction ARM function. The
 * Display pointer literal immediately after it is deliberately excluded.
 * This wrapper applies Display's UI scale only while loading GL_PROJECTION.
 * Its call at0x135d88 targets the original glScalef import at code offset0x27c.
 */
static const unsigned char original_scale[] = {
    0x70,0x40,0x2d,0xe9, 0x68,0x50,0x9f,0xe5, 0x00,0x40,0xa0,0xe1,
    0x00,0x00,0x95,0xe5, 0x0c,0x00,0xd0,0xe5, 0x00,0x00,0x50,0xe3,
    0x04,0x00,0xa0,0x01, 0x70,0x40,0xbd,0x08, 0xba,0x28,0xfb,0x0a,
    0xb8,0x28,0xfb,0xeb, 0x00,0x00,0x95,0xe5, 0x08,0x00,0x90,0xe5,
    0x00,0x20,0xa0,0xe1, 0x00,0x10,0xa0,0xe1, 0x3b,0x29,0xfb,0xeb,
    0x00,0x00,0x95,0xe5, 0x00,0x20,0xa0,0xe3, 0x20,0x10,0x90,0xe5,
    0x24,0x00,0x90,0xe5, 0xfe,0x35,0xa0,0xe3, 0x00,0x00,0x51,0xe1,
    0xad,0x07,0xa0,0xc3, 0x00,0x00,0xa0,0xd3, 0x01,0x01,0x80,0xc2,
    0x02,0x10,0xa0,0xe1, 0x2e,0x29,0xfb,0xeb, 0x04,0x00,0xa0,0xe1,
    0x70,0x40,0xbd,0xe8, 0x1d,0x29,0xfb,0xea
};
/* E3A025FE = MOV r2,#0x3f800000 = IEEE754 float1.0.
 * Previously E1A02000 = MOV r2,r0 copied the XY screen scale into Z as well.
 */
static const unsigned char z_one[] = {0xfe,0x25,0xa0,0xe3};
_Static_assert(PROJECTION_LOAD + sizeof(original_scale) <= GAME_CODE_EXTENT,
               "UI projection fingerprint must fit inside the pinned code extent");

int s3ce_patch_ui_depth(void *allocation, size_t allocation_length,
                        const void *flush_start, uint32_t flush_length) {
    uintptr_t base = (uintptr_t)allocation;
    if (!allocation || flush_start != allocation || (base & 3u) ||
        allocation_length < GAME_CODE_EXTENT || flush_length < GAME_CODE_EXTENT ||
        flush_length > allocation_length || base > UINTPTR_MAX - allocation_length)
        return 0;
    unsigned char *function = (unsigned char *)allocation + PROJECTION_LOAD;
    if (memcmp(function, original_scale, Z_ARGUMENT) ||
        memcmp(function + Z_ARGUMENT + sizeof(z_one),
               original_scale + Z_ARGUMENT + sizeof(z_one),
               sizeof(original_scale) - Z_ARGUMENT - sizeof(z_one))) return -1;
    if (!memcmp(function + Z_ARGUMENT, z_one, sizeof(z_one))) return 2;
    if (memcmp(function + Z_ARGUMENT, original_scale + Z_ARGUMENT, sizeof(z_one))) return -1;
    memcpy(function + Z_ARGUMENT, z_one, sizeof(z_one));
    return 1;
}
