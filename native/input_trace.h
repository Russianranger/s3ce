#ifndef S3CE_INPUT_TRACE_H
#define S3CE_INPUT_TRACE_H
#include <jni.h>
#include <stdint.h>

typedef void (*s3ce_input_motion)(JNIEnv *, jobject, jint, jint, jint, jint);
typedef void (*s3ce_input_log)(int priority, const char *format, ...);

/* Configure once during bootstrap, before RegisterNatives/the game starts.
 * pointer_globals is the pinned runtime's 48-byte g_s3ePointerGlobals, or NULL.
 * The returned wrapper preserves the original JNI arguments and pending Java
 * exception. It calls no JNI functions and does not acquire the engine mutex.
 * State samples are observational: UI input and game polling may run together.
 * Logs the first 256 events, then bounded aggregate records on DOWN/UP:
 * the next 32 boundaries and subsequent power-of-two boundary counts. Thus
 * later gestures remain observable without an unbounded per-event file log. */
s3ce_input_motion s3ce_input_trace_prepare(s3ce_input_motion original,
                                         const uint8_t *pointer_globals,
                                         s3ce_input_log logger);
#endif
