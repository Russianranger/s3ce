#ifndef S3CE_STACK_BRIDGE_H
#define S3CE_STACK_BRIDGE_H
#include <stdint.h>
#include "graphics_diagnostics.h"
/* Execute synchronously on the current pthread's registered stack. The gateway
 * is the original ARM s3eStackSwitchCallS3EFuncR12_Void wrapper (not its core).
 * No thread is created and no EGL state is moved between threads. */
int s3ce_call_on_thread_stack(void (*work)(void), const uintptr_t *loader_sp_slot,
                               void (*gateway)(void), s3ce_graphics_log logger);
#endif
