#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>
#include <signal.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include "../graphics_safety.c"

static EGLContext current_context;
static unsigned driver_calls, initializer_calls;
static GLenum driver_name;
static const char *extension_result;
static int null_result, nested_query, jni_pending;
EGLContext eglGetCurrentContext(void) { return current_context; }
EGLint eglGetError(void) { return 0x3000; }
void android_set_abort_message(const char *message) {
    assert(strstr(message, "S3CE GL initialization failed:"));
}
static void test_log(int priority, const char *format, ...) { (void)priority; (void)format; }
static int test_exception_status(void) { return jni_pending; }
static const GLubyte *test_driver(GLenum name) {
    assert(current_context != EGL_NO_CONTEXT);
    ++driver_calls;
    driver_name = name;
    if (null_result) return NULL;
    if (name == GL_EXTENSIONS) return (const GLubyte *)extension_result;
    return (const GLubyte *)"driver-result";
}
static void initialize_window(void) {
    ++initializer_calls;
    current_context = (EGLContext)(uintptr_t)1;
    if (nested_query) {
        /* Queries during initialization are safe once the real context is bound. */
        assert(s3ce_safe_gl_get_string(GL_VERSION));
    }
}
static void initialize_with_exception(void) {
    ++initializer_calls;
    current_context = (EGLContext)(uintptr_t)1;
    jni_pending = 1;
}
static void initialize_without_context(void) { ++initializer_calls; }
static void initialize_recursive(void) { (void)s3ce_safe_gl_get_string(GL_VERSION); }
static void expect_initialization_abort(void (*initializer)(void)) {
    pid_t child = fork();
    assert(child >= 0);
    if (!child) {
        struct rlimit no_core = {0,0};
        setrlimit(RLIMIT_CORE, &no_core);
        current_context = EGL_NO_CONTEXT;
        initializing_context = 0;
        void *slot = (void *)(uintptr_t)&test_driver;
        s3ce_gl_safety_bind(&slot, test_log, initializer, test_exception_status);
        (void)s3ce_safe_gl_get_string(GL_EXTENSIONS);
        _exit(99);
    }
    int status;
    assert(waitpid(child, &status, 0) == child);
    assert(WIFSIGNALED(status) && WTERMSIG(status) == SIGABRT);
}
int main(void) {
    void *slot = (void *)(uintptr_t)&test_driver;
    s3ce_gl_safety_bind(&slot, test_log, initialize_window, test_exception_status);
    assert(!strcmp((const char *)s3ce_safe_gl_get_string(GL_VERSION), "driver-result"));
    assert(initializer_calls == 1 && driver_calls == 1 && current_context != EGL_NO_CONTEXT);
    const GLubyte *expected = test_driver(GL_VERSION);
    unsigned before = driver_calls;
    assert(s3ce_safe_gl_get_string(GL_VERSION) == expected);
    assert(driver_calls == before+1 && driver_name == GL_VERSION && initializer_calls == 1);
    extension_result = "GL_before GL_OES_framebuffer_object GL_after";
    assert(!strcmp((const char *)s3ce_safe_gl_get_string(GL_EXTENSIONS), "GL_before GL_after"));
    extension_result = "GL_OES_framebuffer_object GL_after";
    assert(!strcmp((const char *)s3ce_safe_gl_get_string(GL_EXTENSIONS), "GL_after"));
    extension_result = "GL_before GL_OES_framebuffer_object";
    assert(!strcmp((const char *)s3ce_safe_gl_get_string(GL_EXTENSIONS), "GL_before"));
    extension_result = "GL_OES_framebuffer_object";
    assert(!strcmp((const char *)s3ce_safe_gl_get_string(GL_EXTENSIONS), ""));
    extension_result = "GL_OES_framebuffer_object2 GL_after";
    assert(s3ce_safe_gl_get_string(GL_EXTENSIONS) == (const GLubyte *)extension_result);
    null_result = 1;
    assert(s3ce_safe_gl_get_string(0xffff) == NULL); /* Preserve invalid-enum driver semantics. */
    null_result = 0;
    current_context = EGL_NO_CONTEXT;
    nested_query = 1;
    before = driver_calls;
    assert(s3ce_safe_gl_get_string(GL_VENDOR));
    assert(initializer_calls == 2 && driver_calls == before+2 && initializing_context == 0);
    expect_initialization_abort(initialize_without_context);
    expect_initialization_abort(initialize_recursive);
    expect_initialization_abort(NULL);
    expect_initialization_abort(initialize_with_exception);
    puts("Real context before driver query, nested safety, explicit init failures and legacy filter: PASS");
}
