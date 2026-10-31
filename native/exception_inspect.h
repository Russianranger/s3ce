#ifndef S3CE_EXCEPTION_INSPECT_H
#define S3CE_EXCEPTION_INSPECT_H
#include <jni.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*s3ce_exception_log)(int priority, const char *format, ...);

/* Call on the normal bootstrap/UI stack before starting the game. Partial
 * diagnostic-cache failures are logged and cleared, never made a game blocker.
 * A pre-existing pending exception is left untouched and caching is skipped.
 * Returns the number of cached public Throwable classification classes. */
int s3ce_exception_inspect_cache(JNIEnv *env, s3ce_exception_log logger);

/* Native JNI operations only: no Call*Method, ExceptionDescribe, or reflection.
 * `original` must be a valid Throwable local/global reference. Its classification
 * is the first matching cached public type, not necessarily its exact subclass.
 * If the caller already cleared its pending exception, this leaves none. If an
 * exception is pending at entry, the identical Throwable is restored at exit.
 * The optional private detailMessage field is cached only during bootstrap;
 * denied/unavailable field access never prevents public-type classification. */
void s3ce_describe_throwable(JNIEnv *env, jthrowable original, s3ce_exception_log logger);

#ifdef __cplusplus
}
#endif
#endif
