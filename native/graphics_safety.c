/* Airplay's early capability queries need a real context. Reuse its original
 * window-context startup callback on the engine thread before entering GLES.
 * The game dereferences extension strings, so failure must stop explicitly.
 */
#include "graphics_safety.h"
#include <EGL/egl.h>
#include <GLES/gl.h>
#include <android/log.h>
#include <android/set_abort_message.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void **get_string_slot;
static s3ce_graphics_log safety_logger;
static void (*initialize_context)(void);
static int (*exception_status)(void);
static _Thread_local unsigned initializing_context;
static char filtered_extensions[32768];

void s3ce_gl_safety_bind(void **driver_slot, s3ce_graphics_log logger,
                         void (*initialize_window_context)(void),
                         int (*jni_exception_status)(void)) {
    get_string_slot = driver_slot;
    safety_logger = logger;
    initialize_context = initialize_window_context;
    exception_status = jni_exception_status;
}

static _Noreturn void context_failure(const char *reason, unsigned name) {
    int pending = exception_status ? exception_status() : -1;
    EGLint error = eglGetError();
    char message[384];
    snprintf(message, sizeof(message),
        "S3CE GL initialization failed: %s (query=0x%x EGL error=0x%x JNI exception=%d)",
        reason, name, error, pending);
    if (safety_logger) safety_logger(ANDROID_LOG_ERROR, "%s", message);
    android_set_abort_message(message);
    abort();
}

const unsigned char *s3ce_safe_gl_get_string(unsigned name) {
    if (eglGetCurrentContext() == EGL_NO_CONTEXT) {
        if (initializing_context)
            context_failure("recursive query before window context became current", name);
        if (!initialize_context)
            context_failure("missing original window-context initializer", name);
        initializing_context = 1;
        if (safety_logger) safety_logger(ANDROID_LOG_INFO,
            "GL window initialization begin on engine thread; query=0x%x JNI exception=%d", name,
            exception_status ? exception_status() : -1);
        initialize_context();
        initializing_context = 0;
        EGLContext current = eglGetCurrentContext();
        int pending_exception = exception_status ? exception_status() : -1;
        if (safety_logger) safety_logger(ANDROID_LOG_INFO,
            "GL window initialization returned; current=%p JNI exception=%d", (void *)current,
            pending_exception);
        if (pending_exception > 0)
            context_failure("pending Java exception after window initialization", name);
        if (current == EGL_NO_CONTEXT)
            context_failure("window initialization callback returned without a current EGL context", name);
    }
    if (!get_string_slot || !*get_string_slot)
        context_failure("missing real GL string dispatch", name);
    const GLubyte *(*driver)(GLenum) = (const GLubyte *(*)(GLenum))*get_string_slot;
    const GLubyte *result = driver(name);
    if (!result && (name == GL_VERSION || name == GL_VENDOR || name == GL_RENDERER || name == GL_EXTENSIONS))
        context_failure("driver returned NULL for a required capability string", name);
    if (!result || name != GL_EXTENSIONS) return result;

    /* Preserve the original Airplay wrapper's intentional FBO-extension filter.
     * Unlike that old wrapper, a NULL result is checked before string access. */
    static const char hidden[] = "GL_OES_framebuffer_object";
    const char *source = (const char *)result;
    const char *at = source;
    while ((at = strstr(at, hidden)) != NULL) {
        const char *end = at + sizeof(hidden) - 1;
        if ((at == source || at[-1] == ' ') && (*end == 0 || *end == ' ')) {
            size_t length = strlen(source);
            if (length >= sizeof(filtered_extensions)) {
                if (safety_logger) safety_logger(ANDROID_LOG_ERROR,
                    "GL extension string exceeds guarded wrapper capacity");
                context_failure("GL extension string exceeds filter capacity", name);
            }
            const char *from = at;
            if (from != source && from[-1] == ' ') --from;
            else if (*end == ' ') ++end;
            size_t prefix = (size_t)(from - source);
            memcpy(filtered_extensions, source, prefix);
            memcpy(filtered_extensions + prefix, end, strlen(end) + 1);
            return (const GLubyte *)filtered_extensions;
        }
        at = end;
    }
    return result;
}
