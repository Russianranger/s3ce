#include "jni_gl_start.h"
#include <android/log.h>

static jclass diagnostic_class;
static jmethodID record_failure;

int s3ce_prepare_java_gl_diagnostics(JNIEnv *env, s3ce_graphics_log logger) {
    if (diagnostic_class && record_failure) return 0;
    if (!env || (*env)->ExceptionCheck(env)) return -1;
    jclass local = (*env)->FindClass(env, "com/ideaworks3d/thesims3/GameDiagnostics");
    if (!local || (*env)->ExceptionCheck(env)) return -1;
    jmethodID method = (*env)->GetStaticMethodID(env, local, "recordGlFailure", "(Ljava/lang/Throwable;)V");
    if (!method || (*env)->ExceptionCheck(env)) {
        (*env)->DeleteLocalRef(env, local);
        return -1;
    }
    jclass global = (jclass)(*env)->NewGlobalRef(env, local);
    (*env)->DeleteLocalRef(env, local);
    if (!global || (*env)->ExceptionCheck(env)) return -1;
    diagnostic_class = global;
    record_failure = method;
    if (logger) logger(ANDROID_LOG_INFO, "Typed GL diagnostic Java helper cached");
    return 0;
}

void s3ce_record_pending_gl_exception(JNIEnv *env, s3ce_graphics_log logger) {
    if (!env || !(*env)->ExceptionCheck(env)) return;
    if (!diagnostic_class || !record_failure) {
        if (logger) logger(ANDROID_LOG_ERROR, "Pending GL exception retained; diagnostic helper unavailable");
        return;
    }
    jthrowable original = (*env)->ExceptionOccurred(env);
    if (!original) return;
    /* Calling Java while an exception is pending is invalid JNI. Temporarily
     * clear only to persist it, discard any logging failure, then restore it. */
    (*env)->ExceptionClear(env);
    jvalue arguments[1] = {{.l = original}};
    (*env)->CallStaticVoidMethodA(env, diagnostic_class, record_failure, arguments);
    if ((*env)->ExceptionCheck(env)) {
        if (logger) logger(ANDROID_LOG_ERROR, "GL exception logger failed; retaining the original Throwable");
        (*env)->ExceptionClear(env);
    }
    if ((*env)->Throw(env, original) != JNI_OK && logger)
        logger(ANDROID_LOG_ERROR, "Failed to restore original pending GL Throwable");
    (*env)->DeleteLocalRef(env, original);
}

int s3ce_call_java_gl_init(JNIEnv *env, jobject thread, jmethodID cached_private,
                           jint version, jmethodID *fresh_private_out,
                           s3ce_graphics_log logger) {
    if (fresh_private_out) *fresh_private_out = NULL;
    if (!env || !thread) return -1;
    if ((*env)->ExceptionCheck(env)) {
        s3ce_record_pending_gl_exception(env, logger);
        return -1;
    }
    jclass receiver_class = (*env)->GetObjectClass(env, thread);
    if (!receiver_class || (*env)->ExceptionCheck(env)) {
        if (logger) logger(ANDROID_LOG_ERROR, "Typed GL bootstrap: receiver class lookup failed");
        s3ce_record_pending_gl_exception(env, logger);
        return -1;
    }
    jmethodID fresh_private = (*env)->GetMethodID(env, receiver_class, "glInit", "(I)V");
    if (!fresh_private || (*env)->ExceptionCheck(env)) {
        if (logger) logger(ANDROID_LOG_ERROR, "Typed GL bootstrap: original glInit(I)V lookup failed");
        s3ce_record_pending_gl_exception(env, logger);
        (*env)->DeleteLocalRef(env, receiver_class);
        return -1;
    }
    if (fresh_private_out) *fresh_private_out = fresh_private;
    jmethodID bridge = (*env)->GetMethodID(env, receiver_class, "compatGlInit", "(I)V");
    if (!bridge || (*env)->ExceptionCheck(env)) {
        if (logger) logger(ANDROID_LOG_ERROR, "Typed GL bootstrap: compatGlInit(I)V lookup failed");
        s3ce_record_pending_gl_exception(env, logger);
        (*env)->DeleteLocalRef(env, receiver_class);
        return -1;
    }
    if (logger) logger(ANDROID_LOG_INFO,
        "Typed GL bootstrap begin: receiver=%p class=%p cached=%p fresh=%p equal=%d bridge=%p version=%d",
        (void *)thread, (void *)receiver_class, (void *)cached_private, (void *)fresh_private,
        cached_private == fresh_private, (void *)bridge, version);
    jvalue arguments[1] = {{.i = version}};
    (*env)->CallVoidMethodA(env, thread, bridge, arguments);
    int pending = (*env)->ExceptionCheck(env) ? 1 : 0;
    if (logger) logger(pending ? ANDROID_LOG_ERROR : ANDROID_LOG_INFO,
        "Typed GL bootstrap returned: JNI exception=%d", pending);
    if (pending) s3ce_record_pending_gl_exception(env, logger);
    (*env)->DeleteLocalRef(env, receiver_class);
    return pending ? -1 : 0;
}
