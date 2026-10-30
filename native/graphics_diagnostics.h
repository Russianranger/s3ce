#ifndef S3CE_GRAPHICS_DIAGNOSTICS_H
#define S3CE_GRAPHICS_DIAGNOSTICS_H
/* Return the original symbol or a transparent, bounded diagnostics wrapper. */
typedef void (*s3ce_graphics_log)(int priority, const char *format, ...);
void *s3ce_graphics_symbol(void *handle, const char *name, void *actual,
                          s3ce_graphics_log logger);
#endif
