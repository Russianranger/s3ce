#include "exception_inspect.h"
#include <assert.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct fake_class { char name[96]; } classes[24];
struct fake_throwable { const char *type; const char *message; };
static struct fake_throwable auxiliary = {"java/lang/NoSuchFieldError", "diagnostic failure"};
static int class_count, fail_class_once = 1, fail_field_once = 1, fail_type_once, fail_region_once;
static int method_calls, throw_calls, field_calls, region_calls;
static jthrowable pending;
static char logs[16384];
static void log_message(int priority, const char *format, ...) {
    (void)priority;
    size_t at = strlen(logs);
    va_list args;
    va_start(args, format);
    vsnprintf(logs + at, sizeof(logs) - at, format, args);
    va_end(args);
    at = strlen(logs);
    if (at + 1 < sizeof(logs)) { logs[at] = '\n'; logs[at + 1] = 0; }
}
static jclass JNICALL find_class(JNIEnv *env, const char *name) {
    (void)env;
    assert(!pending);
    if (fail_class_once && !strcmp(name, "java/lang/NoSuchMethodError")) {
        fail_class_once = 0; pending = (jthrowable)&auxiliary; return NULL;
    }
    for (int i = 0; i < class_count; ++i)
        if (!strcmp(classes[i].name, name)) return (jclass)&classes[i];
    assert(class_count < 24);
    snprintf(classes[class_count].name, sizeof(classes[class_count].name), "%s", name);
    return (jclass)&classes[class_count++];
}
static jobject JNICALL global_ref(JNIEnv *env, jobject object) { (void)env; assert(!pending); return object; }
static void JNICALL delete_ref(JNIEnv *env, jobject object) { (void)env; (void)object; }
static jboolean JNICALL exception_check(JNIEnv *env) { (void)env; return pending != NULL; }
static jthrowable JNICALL exception_occurred(JNIEnv *env) { (void)env; return pending; }
static void JNICALL exception_clear(JNIEnv *env) { (void)env; pending = NULL; }
static jint JNICALL throw_same(JNIEnv *env, jthrowable error) { (void)env; ++throw_calls; pending = error; return JNI_OK; }
static jfieldID JNICALL get_field(JNIEnv *env, jclass type, const char *name, const char *signature) {
    (void)env; assert(!pending); ++field_calls;
    assert(!strcmp(((struct fake_class *)type)->name, "java/lang/Throwable"));
    assert(!strcmp(name, "detailMessage") && !strcmp(signature, "Ljava/lang/String;"));
    if (fail_field_once) { fail_field_once = 0; pending = (jthrowable)&auxiliary; return NULL; }
    return (jfieldID)(uintptr_t)1;
}
static jboolean JNICALL instance_of(JNIEnv *env, jobject object, jclass type) {
    (void)env; assert(!pending);
    if (fail_type_once) { fail_type_once = 0; pending = (jthrowable)&auxiliary; return JNI_FALSE; }
    struct fake_throwable *error = (struct fake_throwable *)object;
    const char *name = ((struct fake_class *)type)->name;
    return !strcmp(name, error->type) || !strcmp(name, "java/lang/Throwable");
}
static jobject JNICALL object_field(JNIEnv *env, jobject object, jfieldID field) {
    (void)env; assert(!pending && field == (jfieldID)(uintptr_t)1);
    return (jobject)((struct fake_throwable *)object)->message;
}
static jsize JNICALL string_length(JNIEnv *env, jstring text) { (void)env; assert(!pending); return (jsize)strlen((const char *)text); }
static void JNICALL string_region(JNIEnv *env, jstring text, jsize start, jsize length, char *output) {
    (void)env; assert(!pending); ++region_calls;
    if (fail_region_once) { fail_region_once = 0; pending = (jthrowable)&auxiliary; return; }
    assert(start == 0 && length <= 256);
    memcpy(output, (const char *)text + start, (size_t)length);
}
static void JNICALL forbidden_java_call(JNIEnv *env, jobject object, jmethodID method, const jvalue *args) {
    (void)env; (void)object; (void)method; (void)args; ++method_calls;
    assert(!"Native Throwable inspection must not invoke Java methods");
}
int main(void) {
    const struct JNINativeInterface_ functions = {
        .FindClass = find_class, .NewGlobalRef = global_ref,
        .DeleteLocalRef = delete_ref, .DeleteGlobalRef = delete_ref,
        .ExceptionCheck = exception_check, .ExceptionOccurred = exception_occurred,
        .ExceptionClear = exception_clear, .Throw = throw_same,
        .GetFieldID = get_field, .GetObjectField = object_field, .IsInstanceOf = instance_of,
        .GetStringLength = string_length, .GetStringUTFRegion = string_region,
        .CallVoidMethodA = forbidden_java_call, .CallStaticVoidMethodA = forbidden_java_call
    };
    JNIEnv env = &functions;
    assert(s3ce_exception_inspect_cache(&env, log_message) == 16);
    assert(!pending && strstr(logs, "class unavailable") && strstr(logs, "detailMessage field unavailable"));
    struct fake_throwable overflow = {"java/lang/StackOverflowError", "stack size 1036KB"};
    pending = (jthrowable)&overflow;
    s3ce_describe_throwable(&env, (jthrowable)&overflow, log_message);
    assert(pending == (jthrowable)&overflow && throw_calls == 1);
    assert(strstr(logs, "is-a=java/lang/StackOverflowError") && strstr(logs, "[detail unavailable]"));
    int old_fields = field_calls;
    assert(s3ce_exception_inspect_cache(&env, log_message) == 16);
    assert(pending == (jthrowable)&overflow && field_calls == old_fields);
    pending = NULL;
    assert(s3ce_exception_inspect_cache(&env, log_message) == 17);
    assert(!pending);
    logs[0] = 0;
    pending = (jthrowable)&overflow;
    s3ce_describe_throwable(&env, (jthrowable)&overflow, log_message);
    assert(pending == (jthrowable)&overflow && strstr(logs, "detail=stack size 1036KB"));
    struct fake_throwable oom = {"java/lang/OutOfMemoryError", NULL};
    pending = NULL; logs[0] = 0;
    s3ce_describe_throwable(&env, (jthrowable)&oom, log_message);
    assert(!pending && strstr(logs, "OutOfMemoryError") && strstr(logs, "[no detail message]"));
    logs[0] = 0; pending = (jthrowable)&overflow; fail_type_once = 1;
    s3ce_describe_throwable(&env, (jthrowable)&overflow, log_message);
    assert(pending == (jthrowable)&overflow && strstr(logs, "diagnostic JNI failure"));
    logs[0] = 0; pending = (jthrowable)&overflow; fail_region_once = 1;
    s3ce_describe_throwable(&env, (jthrowable)&overflow, log_message);
    assert(pending == (jthrowable)&overflow && strstr(logs, "[detail unavailable]"));
    char long_message[600]; memset(long_message, 'x', sizeof(long_message) - 1); long_message[599] = 0;
    struct fake_throwable long_error = {"java/lang/VerifyError", long_message};
    pending = NULL; logs[0] = 0;
    s3ce_describe_throwable(&env, (jthrowable)&long_error, log_message);
    assert(!pending && strstr(logs, "VerifyError") && strstr(logs, "[truncated]"));
    assert(method_calls == 0 && region_calls >= 4);
    puts("PASS: native-only Throwable type/detail, partial cache recovery, bounded strings, and same-pending preservation across diagnostic failures.");
    return 0;
}
