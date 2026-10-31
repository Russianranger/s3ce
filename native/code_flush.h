#ifndef S3CE_CODE_FLUSH_H
#define S3CE_CODE_FLUSH_H
#include <stddef.h>
#include <stdint.h>
/* Forward through the original mprotect+I-cache routine. Expand only a known
 * dedicated code allocation, covering generated import and callback veneers. */
int s3ce_flush_code_span(void *start, uint32_t length, void *allocation,
                          size_t allocation_length,
                          int (*platform_flush)(void *, uint32_t));
#endif
