#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include "../jni_gl_start.c"

static jobject receiver = (jobject)(uintptr_t)0x1100;
static jclass receiver_class = (jclass)(uintptr_t)0x2200;
static jmethodID private_id = (jmethodID)(uintptr_t)0x3300;
static jmethodID bridge_id = (jmethodID)(uintptr_t)0x4400;
static jthrowable thrown = (jthrowable)(uintptr_t)0x5500;
static jthrowable logging_failure = (jthrowable)(uintptr_t)0x6600;
static jclass diagnostics = (jclass)(uintptr_t)0x7700;
static jmethodID failure_method = (jmethodID)(uintptr_t)0x8800;
static jthrowable pending;
static unsigned lookups, calls_a, calls_v, deleted_receivers, recorded, clears, restored;
static jint expected_version;
static int throw_on_call, fail_lookup, fail_logger;
static unsigned inspected;
void s3ce_describe_throwable(JNIEnv *env, jthrowable original, s3ce_exception_log logger) {
    (void)env; (void)logger; assert(!pending && original == thrown); ++inspected;
}
static void log_message(int priority, const char *format, ...) { (void)priority; (void)format; }
static jboolean check_exception(JNIEnv *env) { (void)env; return pending ? JNI_TRUE : JNI_FALSE; }
static jthrowable exception_occurred(JNIEnv *env) { (void)env; return pending; }
static void exception_clear(JNIEnv *env) { (void)env; pending = NULL; ++clears; }
static jint throw_exception(JNIEnv *env, jthrowable exception) {
    (void)env; assert(!pending && exception == thrown); pending = exception; ++restored; return JNI_OK;
}
static jclass find_class(JNIEnv *env, const char *name) {
    (void)env; assert(!strcmp(name,"com/ideaworks3d/thesims3/GameDiagnostics")); return diagnostics;
}
static jmethodID static_method(JNIEnv *env, jclass klass, const char *name, const char *signature) {
    (void)env; assert(klass == diagnostics && !strcmp(name,"recordGlFailure")
        && !strcmp(signature,"(Ljava/lang/Throwable;)V")); return failure_method;
}
static jobject global_reference(JNIEnv *env, jobject object) {
    (void)env; assert(object == diagnostics); return object;
}
static void call_static_a(JNIEnv *env, jclass klass, jmethodID method, const jvalue *arguments) {
    (void)env; assert(!pending && klass == diagnostics && method == failure_method);
    assert(arguments && arguments[0].l == thrown);
    ++recorded;
    if (fail_logger) pending = logging_failure;
}
static jclass object_class(JNIEnv *env, jobject object) {
    (void)env; assert(object == receiver); return receiver_class;
}
static jmethodID method_id(JNIEnv *env, jclass klass, const char *name, const char *signature) {
    (void)env; assert(klass == receiver_class && !strcmp(signature, "(I)V"));
    ++lookups;
    if (fail_lookup) { pending = thrown; return NULL; }
    if (!strcmp(name, "glInit")) return private_id;
    assert(!strcmp(name, "compatGlInit"));
    return bridge_id;
}
static void delete_reference(JNIEnv *env, jobject object) {
    (void)env;
    assert(object == receiver_class || object == diagnostics || object == thrown);
    if (object == receiver_class) ++deleted_receivers;
}
static void call_a(JNIEnv *env, jobject object, jmethodID method, const jvalue *arguments) {
    (void)env; assert(object == receiver && method == bridge_id);
    assert(arguments && arguments[0].i == expected_version);
    ++calls_a;
    if (throw_on_call) pending = thrown;
}
static void call_v(JNIEnv *env, jobject object, jmethodID method, va_list arguments) {
    (void)env; (void)object; (void)method; (void)arguments;
    ++calls_v;
    assert(!"The typed bridge must not use CallVoidMethodV");
}
int main(void) {
    struct JNINativeInterface table = {0};
    table.FindClass = find_class;
    table.GetStaticMethodID = static_method;
    table.NewGlobalRef = global_reference;
    table.CallStaticVoidMethodA = call_static_a;
    table.ExceptionOccurred = exception_occurred;
    table.ExceptionClear = exception_clear;
    table.Throw = throw_exception;
    table.GetObjectClass = object_class;
    table.GetMethodID = method_id;
    table.DeleteLocalRef = delete_reference;
    table.CallVoidMethodA = call_a;
    table.CallVoidMethodV = call_v;
    table.ExceptionCheck = check_exception;
    JNIEnv environment = &table;
    assert(s3ce_prepare_java_gl_diagnostics(&environment, log_message) == 0);
    expected_version = 1;
    jmethodID resolved = NULL;
    assert(s3ce_call_java_gl_init(&environment, receiver, (jmethodID)(uintptr_t)0xdead, 1, &resolved, log_message) == 0);
    assert(resolved == private_id && lookups == 2 && calls_a == 1 && calls_v == 0 && deleted_receivers == 1);
    expected_version = 2;
    resolved = NULL;
    assert(s3ce_call_java_gl_init(&environment, receiver, NULL, 2, &resolved, log_message) == 0);
    assert(resolved == private_id && lookups == 4 && calls_a == 2 && calls_v == 0 && deleted_receivers == 2);
    throw_on_call = 1;
    assert(s3ce_call_java_gl_init(&environment, receiver, private_id, 2, &resolved, log_message) == -1);
    assert(pending == thrown && calls_a == 3 && calls_v == 0 && deleted_receivers == 3);
    assert(recorded == 1 && clears == 1 && restored == 1);
    /* Even a failure in the Java diagnostic helper must not replace the original. */
    pending = NULL;
    fail_logger = 1;
    assert(s3ce_call_java_gl_init(&environment, receiver, private_id, 2, &resolved, log_message) == -1);
    assert(pending == thrown && recorded == 2 && clears == 3 && restored == 2);
    unsigned before = lookups;
    assert(s3ce_call_java_gl_init(&environment, receiver, private_id, 2, &resolved, log_message) == -1);
    assert(pending == thrown && lookups == before && calls_a == 4 && resolved == NULL);
    pending = NULL;
    throw_on_call = 0;
    fail_logger = 0;
    fail_lookup = 1;
    assert(s3ce_call_java_gl_init(&environment, receiver, private_id, 2, &resolved, log_message) == -1);
    assert(pending == thrown && calls_a == 4 && deleted_receivers == 5 && resolved == NULL);
    assert(recorded == 4 && restored == 4 && inspected == 4);
    puts("Typed JNI arguments/cache output and same-Throwable persistence/restoration: PASS");
}
