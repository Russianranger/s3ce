#ifndef S3CE_GAME_POINTER_OBSERVER_H
#define S3CE_GAME_POINTER_OBSERVER_H
#include <stddef.h>
#include <stdint.h>

/* Must validate the complete readable range and copy it, returning1 on success
 * or0 on failure. The observer never dereferences a runtime address itself. */
typedef int (*s3ce_game_read)(void *context, uintptr_t address, void *out, size_t size);

/* Call synchronously on the engine callback thread, after the original known
 * game callback returns. Returns1 for a recognized snapshot, or0 with a short
 * unavailable reason. Output is always terminated when capacity>0. No JNI,
 * allocations, pointer writes, or callback/gesture state changes occur.
 * The source runtime allocates code and data separately: all globals resolve
 * through the actual relocated literal pools, never code_base+dataVMA. */
int s3ce_observe_game_pointer(uintptr_t code_base, uintptr_t original_callback,
                            s3ce_game_read read, void *context,
                            char *out, size_t capacity);
#endif
