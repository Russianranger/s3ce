/* Diagnose JNI failures even when ART cannot enter any Java method because the
 * preserved S3E program is executing on a heap/fibre stack. Class resolution and
 * optional field-ID lookup happen on the normal bootstrap stack, never here. */
#include "exception_inspect.h"
#include <pthread.h>
#include <stddef.h>
#include <string.h>

#define LOG_INFO 4
#define LOG_WARN 5
#define LOG_ERROR 6
#define MESSAGE_UNITS 256

struct known_throwable {
    const char *name;
    jclass global;
};

/* Keep specific types before their public ancestors. Global references live for
 * this application's VM lifetime; there are no class-loader-dependent names. */
static struct known_throwable types[] = {
    {"java/lang/StackOverflowError", NULL},
    {"java/lang/OutOfMemoryError", NULL},
    {"java/lang/VerifyError", NULL},
    {"java/lang/NoClassDefFoundError", NULL},
    {"java/lang/ExceptionInInitializerError", NULL},
    {"java/lang/NoSuchMethodError", NULL},
    {"java/lang/NoSuchFieldError", NULL},
    {"java/lang/UnsatisfiedLinkError", NULL},
    {"java/lang/IllegalAccessError", NULL},
    {"java/lang/AbstractMethodError", NULL},
    {"java/lang/IncompatibleClassChangeError", NULL},
    {"java/lang/LinkageError", NULL},
    {"java/lang/IllegalStateException", NULL},
    {"java/lang/IllegalArgumentException", NULL},
    {"java/lang/NullPointerException", NULL},
    {"java/lang/RuntimeException", NULL},
    {"java/lang/Throwable", NULL}
};
#define TYPE_COUNT (sizeof(types) / sizeof(types[0]))
static pthread_mutex_t cache_lock = PTHREAD_MUTEX_INITIALIZER;
static jfieldID detail_message;

static int clear_diagnostic_exception(JNIEnv *env) {
    if (!(*env)->ExceptionCheck(env)) return 0;
    (*env)->ExceptionClear(env);
    return 1;
}

static int cached_count(void) {
    int count = 0;
    pthread_mutex_lock(&cache_lock);
    for (size_t i = 0; i < TYPE_COUNT; ++i) count += types[i].global != NULL;
    pthread_mutex_unlock(&cache_lock);
    return count;
}

int s3ce_exception_inspect_cache(JNIEnv *env, s3ce_exception_log logger) {
    if (!env) return 0;
    if ((*env)->ExceptionCheck(env)) {
        if (logger) logger(LOG_WARN, "Native Throwable cache skipped: a Java exception was already pending");
        return cached_count();
    }
    for (size_t i = 0; i < TYPE_COUNT; ++i) {
        pthread_mutex_lock(&cache_lock);
        int present = types[i].global != NULL;
        pthread_mutex_unlock(&cache_lock);
        if (present) continue;
        jclass local = (*env)->FindClass(env, types[i].name);
        int failed = clear_diagnostic_exception(env);
        if (failed || !local) {
            if (local) (*env)->DeleteLocalRef(env, local);
            if (logger) logger(LOG_WARN, "Native Throwable class unavailable: %s", types[i].name);
            continue;
        }
        jclass global = (jclass)(*env)->NewGlobalRef(env, local);
        (*env)->DeleteLocalRef(env, local);
        failed = clear_diagnostic_exception(env);
        if (failed || !global) {
            if (global) (*env)->DeleteGlobalRef(env, global);
            if (logger) logger(LOG_WARN, "Native Throwable global reference unavailable: %s", types[i].name);
            continue;
        }
        pthread_mutex_lock(&cache_lock);
        if (!types[i].global) { types[i].global = global; global = NULL; }
        pthread_mutex_unlock(&cache_lock);
        if (global) (*env)->DeleteGlobalRef(env, global);
    }
    pthread_mutex_lock(&cache_lock);
    jclass throwable_class = types[TYPE_COUNT - 1].global;
    int needs_field = detail_message == NULL;
    pthread_mutex_unlock(&cache_lock);
    if (throwable_class && needs_field) {
        jfieldID field = (*env)->GetFieldID(env, throwable_class, "detailMessage", "Ljava/lang/String;");
        int failed = clear_diagnostic_exception(env);
        if (!failed && field) {
            pthread_mutex_lock(&cache_lock);
            if (!detail_message) detail_message = field;
            pthread_mutex_unlock(&cache_lock);
        } else if (logger) {
            logger(LOG_WARN, "Native Throwable detailMessage field unavailable; public-type classification remains enabled");
        }
    }
    int count = cached_count();
    pthread_mutex_lock(&cache_lock);
    int field_present = detail_message != NULL;
    pthread_mutex_unlock(&cache_lock);
    if (logger) logger(LOG_INFO, "Native Throwable inspection cached: types=%d/%zu detailMessage=%d",
                       count, TYPE_COUNT, field_present);
    return count;
}

void s3ce_describe_throwable(JNIEnv *env, jthrowable original, s3ce_exception_log logger) {
    if (!env) return;
    /* ExceptionOccurred creates an owned local reference. Save it before doing
     * anything that might set a secondary diagnostic exception. */
    jthrowable entry_exception = (*env)->ExceptionOccurred(env);
    if (entry_exception) (*env)->ExceptionClear(env);
    if (!original) original = entry_exception;
    jclass cached[TYPE_COUNT];
    pthread_mutex_lock(&cache_lock);
    for (size_t i = 0; i < TYPE_COUNT; ++i) cached[i] = types[i].global;
    jfieldID field = detail_message;
    pthread_mutex_unlock(&cache_lock);
    const char *classification = "unclassified Throwable";
    const char *detail_status = "[detail unavailable]";
    char message[MESSAGE_UNITS * 3 + 1] = {0};
    int truncated = 0;
    if (!original) {
        classification = "no Throwable supplied";
    } else {
        for (size_t i = 0; i < TYPE_COUNT; ++i) {
            if (!cached[i]) continue;
            jboolean matches = (*env)->IsInstanceOf(env, original, cached[i]);
            if (clear_diagnostic_exception(env)) {
                if (logger) logger(LOG_WARN, "Native Throwable classification encountered a diagnostic JNI failure");
                break;
            }
            if (matches) { classification = types[i].name; break; }
        }
        if (field) {
            jstring text = (jstring)(*env)->GetObjectField(env, original, field);
            int failed = clear_diagnostic_exception(env);
            if (!failed && !text) detail_status = "[no detail message]";
            if (!failed && text) {
                jsize length = (*env)->GetStringLength(env, text);
                failed = clear_diagnostic_exception(env);
                if (!failed && length >= 0) {
                    jsize keep = length > MESSAGE_UNITS ? MESSAGE_UNITS : length;
                    (*env)->GetStringUTFRegion(env, text, 0, keep, message);
                    failed = clear_diagnostic_exception(env);
                    if (!failed) { detail_status = message; truncated = length > keep; }
                }
            }
            if (text) (*env)->DeleteLocalRef(env, text);
        }
    }
    if (logger) logger(LOG_ERROR, "Java Throwable native summary: is-a=%s detail=%s%s",
                       classification, detail_status, truncated ? " [truncated]" : "");
    /* Diagnostic failures must never replace the exception being investigated.
     * Caller-cleared input remains clear; an entry-pending Throwable is restored. */
    clear_diagnostic_exception(env);
    if (entry_exception) {
        (*env)->Throw(env, entry_exception);
        (*env)->DeleteLocalRef(env, entry_exception);
    }
}
