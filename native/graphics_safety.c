/* Airplay queries GL_VERSION before an EGL context is current on its thread. Some modern GLES1
 * dispatch stubs dereference a null per-thread table in that state. Never enter
 * the driver without a current context; let the original caller handle NULL.
 */
#include "graphics_safety.h"
#include <EGL/egl.h>
#include <GLES/gl.h>
#include <android/log.h>
#include <string.h>

static void **get_string_slot;
static s3ce_graphics_log safety_logger;
static unsigned blocked_queries;
static char filtered_extensions[32768];

void s3ce_gl_safety_bind(void **driver_slot, s3ce_graphics_log logger) {
    get_string_slot = driver_slot;
    safety_logger = logger;
}

const unsigned char *s3ce_safe_gl_get_string(unsigned name) {
    if (eglGetCurrentContext() == EGL_NO_CONTEXT) {
        if (blocked_queries++ < 8 && safety_logger)
            safety_logger(ANDROID_LOG_INFO,
                "GL string query 0x%x deferred: no EGL context on current thread", name);
        return NULL;
    }
    if (!get_string_slot || !*get_string_slot) return NULL;
    const GLubyte *(*driver)(GLenum) = (const GLubyte *(*)(GLenum))*get_string_slot;
    const GLubyte *result = driver(name);
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
                return NULL;
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
