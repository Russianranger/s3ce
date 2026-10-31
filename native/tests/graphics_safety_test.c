#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>
#include "../graphics_safety.c"

static EGLContext current_context;
static unsigned driver_calls;
static GLenum driver_name;
static const char *extension_result;
static int null_result;
EGLContext eglGetCurrentContext(void) { return current_context; }
static void test_log(int priority, const char *format, ...) { (void)priority; (void)format; }
static const GLubyte *test_driver(GLenum name) {
    /* Reaching the driver without a current context models the actual crash. */
    assert(current_context != EGL_NO_CONTEXT);
    ++driver_calls;
    driver_name = name;
    if (null_result) return NULL;
    if (name == GL_EXTENSIONS) return (const GLubyte *)extension_result;
    return (const GLubyte *)"driver-result";
}
int main(void) {
    void *slot = (void *)(uintptr_t)&test_driver;
    s3ce_gl_safety_bind(&slot, test_log);
    /* All pre-context string queries must return NULL without driver dispatch. */
    const GLenum names[] = {GL_VERSION, GL_VENDOR, GL_RENDERER, GL_EXTENSIONS, 0xffff};
    for (unsigned i = 0; i < sizeof(names)/sizeof(names[0]); ++i)
        assert(s3ce_safe_gl_get_string(names[i]) == NULL);
    assert(driver_calls == 0);
    current_context = (EGLContext)(uintptr_t)1;
    const GLubyte *expected = test_driver(GL_VERSION);
    unsigned before = driver_calls;
    assert(s3ce_safe_gl_get_string(GL_VERSION) == expected);
    assert(driver_calls == before+1 && driver_name == GL_VERSION);
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
    assert(s3ce_safe_gl_get_string(GL_EXTENSIONS) == NULL);
    current_context = EGL_NO_CONTEXT;
    before = driver_calls;
    assert(s3ce_safe_gl_get_string(GL_VERSION) == NULL && driver_calls == before);
    current_context = (EGLContext)(uintptr_t)1;
    s3ce_gl_safety_bind(NULL, NULL);
    assert(s3ce_safe_gl_get_string(GL_VERSION) == NULL);
    puts("Pre-context GL driver suppression, current dispatch and legacy extension filter: PASS");
}
