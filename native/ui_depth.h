#ifndef S3CE_UI_DEPTH_H
#define S3CE_UI_DEPTH_H
#include <stddef.h>
#include <stdint.h>

/* Called under the loader's code-allocation lock, before the original full-code
 * mprotect/I-cache flush. Changes only the pinned projection wrapper's Z scale.
 * Returns 1 when patched, 2 when already patched, 0 for a partial/unknown span,
 * and -1 when a complete candidate has an unexpected instruction fingerprint.
 */
int s3ce_patch_ui_depth(void *allocation, size_t allocation_length,
                        const void *flush_start, uint32_t flush_length);
#endif
