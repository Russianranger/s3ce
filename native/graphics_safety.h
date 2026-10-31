#ifndef S3CE_GRAPHICS_SAFETY_H
#define S3CE_GRAPHICS_SAFETY_H
#include "graphics_diagnostics.h"
/* Bind the original Airplay wrapper's real glGetString dispatch slot. */
void s3ce_gl_safety_bind(void **driver_slot, s3ce_graphics_log logger,
                         void (*initialize_window_context)(void),
                         int (*jni_exception_status)(void));
/* Replacement for the original wrapper; also active in original-renderer mode. */
const unsigned char *s3ce_safe_gl_get_string(unsigned name);
#endif
