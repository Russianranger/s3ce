#ifndef S3CE_JNI_GL_START_H
#define S3CE_JNI_GL_START_H
#include <jni.h>
#include "graphics_diagnostics.h"
/* Cache the application-owned diagnostic class on the bootstrap UI JNI call. */
int s3ce_prepare_java_gl_diagnostics(JNIEnv *env, s3ce_graphics_log logger);
/* Persist a pending Throwable, then restore the same exception before returning. */
void s3ce_record_pending_gl_exception(JNIEnv *env, s3ce_graphics_log logger);
/* Resolve the current receiver's typed bridge; do not consume Java failures. */
int s3ce_call_java_gl_init(JNIEnv *env, jobject thread, jmethodID cached_private,
                           jint version, jmethodID *fresh_private_out,
                           s3ce_graphics_log logger);
#endif
