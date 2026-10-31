/* Bounded diagnostics and conditional software PVRTC1 texture compatibility.
 * Other formats and native-capable drivers retain their original upload path.
 * Error flags consumed for diagnosis are returned by the wrapped glGetError.
 */
#include "graphics_diagnostics.h"
#include "pvrtc/pvrtc_bridge.h"
#include <GLES/gl.h>
#include <android/log.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static s3ce_graphics_log log_graphics;
static const GLubyte *(*real_get_string)(GLenum);
static GLenum (*real_get_error)(void);
static void *(*real_get_proc)(const char *);
static void (*real_tex_image)(GLenum, GLint, GLint, GLsizei, GLsizei, GLint, GLenum, GLenum, const void *);
static void (*real_compressed_image)(GLenum, GLint, GLenum, GLsizei, GLsizei, GLint, GLsizei, const void *);
static void (*real_compressed_sub_image)(GLenum, GLint, GLint, GLint, GLsizei, GLsizei, GLenum, GLsizei, const void *);
static void (*real_tex_sub_image)(GLenum, GLint, GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, const void *);
static void (*real_draw_arrays)(GLenum, GLint, GLsizei);
static void (*real_draw_elements)(GLenum, GLsizei, GLenum, const void *);
static void (*real_alpha_func)(GLenum, GLclampf);
static void (*real_alpha_funcx)(GLenum, GLclampx);
static void (*real_blend_func)(GLenum, GLenum);
static _Thread_local GLenum pending_errors[16];
static _Thread_local unsigned pending_count;
static unsigned texture_calls, draw_calls, alpha_calls, blend_calls, logged_errors;
static unsigned context_logged;
static int driver_pvrtc = -1;
static char software_extensions[32768];
static unsigned fallback_uploads, fallback_failures, fallback_attempts, string_calls;
#define PVRTC_EXTENSION "GL_IMG_texture_compression_pvrtc"
#define PVRTC_RGB_4BPP 0x8c00
#define PVRTC_RGB_2BPP 0x8c01
#define PVRTC_RGBA_4BPP 0x8c02
#define PVRTC_RGBA_2BPP 0x8c03
#define MAX_DECODED_BYTES (16u * 1024u * 1024u)

static int extension_supported(const char *list, const char *name) {
    if (!list || !name || !name[0]) return 0;
    size_t length = strlen(name);
    const char *at = list;
    while ((at = strstr(at, name)) != NULL) {
        if ((at == list || at[-1] == ' ') && (at[length] == 0 || at[length] == ' ')) return 1;
        at += length;
    }
    return 0;
}

static void remember_error(GLenum error) {
    for (unsigned i = 0; i < pending_count; ++i)
        if (pending_errors[i] == error) return;
    if (pending_count < sizeof(pending_errors) / sizeof(pending_errors[0]))
        pending_errors[pending_count++] = error;
}

static void observe_errors(const char *operation) {
    if (!real_get_error) return;
    /* GL has a finite set of flags. Bound draining in case of a broken driver. */
    for (unsigned i = 0; i < 16; ++i) {
        GLenum error = real_get_error();
        if (error == GL_NO_ERROR) break;
        remember_error(error);
        if (logged_errors++ < 48 && log_graphics)
            log_graphics(ANDROID_LOG_ERROR, "GL error after %s: 0x%x", operation, error);
    }
}

static GLenum diagnosed_get_error(void) {
    if (pending_count) {
        GLenum result = pending_errors[0];
        --pending_count;
        memmove(pending_errors, pending_errors + 1, pending_count * sizeof(*pending_errors));
        return result;
    }
    return real_get_error ? real_get_error() : GL_NO_ERROR;
}

static void describe_context(void) {
    if (context_logged || !real_get_string || !log_graphics) return;
    const GLubyte *version = real_get_string(GL_VERSION);
    if (!version) return;  /* No current context yet. Try on the next real call. */
    context_logged = 1;
    const GLubyte *vendor = real_get_string(GL_VENDOR);
    const GLubyte *renderer = real_get_string(GL_RENDERER);
    const GLubyte *extensions = real_get_string(GL_EXTENSIONS);
    log_graphics(ANDROID_LOG_INFO, "GL version=%s vendor=%s renderer=%s", version,
                 vendor ? (const char *)vendor : "?", renderer ? (const char *)renderer : "?");
    if (extensions) {
        const char *ext = (const char *)extensions;
        driver_pvrtc = extension_supported(ext, PVRTC_EXTENSION);
        log_graphics(ANDROID_LOG_INFO, "GL texture capabilities PVRTC=%d ETC1=%d ATC=%d NPOT=%d draw_texture=%d",
                     driver_pvrtc,
                     strstr(ext, "GL_OES_compressed_ETC1_RGB8_texture") != NULL,
                     strstr(ext, "texture_compression_atitc") != NULL || strstr(ext, "compressed_ATC_texture") != NULL,
                     strstr(ext, "texture_npot") != NULL,
                     strstr(ext, "GL_OES_draw_texture") != NULL);
        /* Complete most mobile extension lists without unbounded log output. */
        size_t length = strlen(ext);
        for (size_t at = 0; at < length && at < 8192; at += 768)
            log_graphics(ANDROID_LOG_INFO, "GL extensions[%zu]=%.*s", at,
                         (int)((length-at < 768) ? length-at : 768), ext+at);
    }
}

static const GLubyte *diagnosed_get_string(GLenum name) {
    unsigned call = string_calls++;
    if (call < 8 && log_graphics)
        log_graphics(ANDROID_LOG_INFO, "GL GetString begin #%u name=0x%x driver=%p", call, name, (void *)real_get_string);
    const GLubyte *result = real_get_string(name);
    if (call < 8 && log_graphics)
        log_graphics(ANDROID_LOG_INFO, "GL GetString returned #%u result=%p", call, (const void *)result);
    describe_context();
    /* This game's verified capability initializer gates PVR asset loading on
     * this exact extension token. Advertising it is safe only because all four
     * PVRTC1 upload formats below have a software implementation. */
    if (name == GL_EXTENSIONS && result && driver_pvrtc == 0 && real_tex_image) {
        if (!software_extensions[0]) {
            size_t length = strlen((const char *)result);
            const size_t token_length = sizeof(PVRTC_EXTENSION) - 1;
            if (length + token_length + 2 < sizeof(software_extensions)) {
                memcpy(software_extensions, result, length);
                software_extensions[length] = ' ';
                memcpy(software_extensions + length + 1, PVRTC_EXTENSION, token_length + 1);
                if (log_graphics) log_graphics(ANDROID_LOG_INFO,
                    "GL PVRTC1 software support advertised; native GPU support absent");
            }
        }
        if (software_extensions[0]) return (const GLubyte *)software_extensions;
    }
    return result;
}

static void diagnosed_tex_image(GLenum target, GLint level, GLint internal,
                                GLsizei width, GLsizei height, GLint border,
                                GLenum format, GLenum type, const void *pixels) {
    describe_context();
    unsigned call = texture_calls++;
    if (call < 48 && log_graphics)
        log_graphics(ANDROID_LOG_INFO, "GL TexImage2D #%u %dx%d level=%d internal=0x%x format=0x%x type=0x%x data=%d",
                     call, width, height, level, internal, format, type, pixels != NULL);
    real_tex_image(target, level, internal, width, height, border, format, type, pixels);
    if (call < 1024) observe_errors("glTexImage2D");
}

/* Decode one complete PVRTC mip level. All extent and minimum-block checks
 * live in the C bridge; ordinary and malformed uploads keep the driver path. */
static unsigned char *decode_pvrtc_image(GLenum internal, GLsizei width,
        GLsizei height, GLsizei bytes, const void *pixels, int *result) {
    *result = -1;
    if (width <= 0 || height <= 0 || width > 4096 || height > 4096 || bytes < 0 || !pixels) return NULL;
    size_t output_size = (size_t)width * (size_t)height * 4;
    if (output_size > MAX_DECODED_BYTES) return NULL;
    unsigned char *rgba = malloc(output_size);
    unsigned bits = (internal == PVRTC_RGB_2BPP || internal == PVRTC_RGBA_2BPP) ? 2 : 4;
    unsigned attempt = fallback_attempts++;
    if (attempt < 8 && log_graphics)
        log_graphics(ANDROID_LOG_INFO, "PVRTC decode begin #%u input=%p bytes=%d %dx%d bpp=%u", attempt, pixels, bytes, width, height, bits);
    *result = rgba ? s3ce_pvrtc_decode(pixels, (size_t)bytes, bits,
        (unsigned)width, (unsigned)height, rgba, output_size) : -2;
    if (attempt < 8 && log_graphics)
        log_graphics(ANDROID_LOG_INFO, "PVRTC decode returned #%u result=%d output=%p", attempt, *result, (void *)rgba);
    if (*result != 0) { free(rgba); return NULL; }
    if (internal == PVRTC_RGB_4BPP || internal == PVRTC_RGB_2BPP)
        for (size_t at = 3; at < output_size; at += 4) rgba[at] = 255;
    return rgba;
}

static void record_decode_failure(int result, GLsizei width, GLsizei height,
                                  GLenum internal, GLsizei bytes) {
    if (fallback_failures++ < 16 && log_graphics)
        log_graphics(ANDROID_LOG_ERROR, "GL PVRTC decode failed result=%d %dx%d format=0x%x bytes=%d",
                     result, width, height, internal, bytes);
}

static void diagnosed_compressed_image(GLenum target, GLint level, GLenum internal,
                                       GLsizei width, GLsizei height, GLint border,
                                       GLsizei bytes, const void *pixels) {
    describe_context();
    unsigned call = texture_calls++;
    if (call < 128 && log_graphics)
        log_graphics(ANDROID_LOG_INFO, "GL CompressedTexImage2D #%u %dx%d level=%d format=0x%x bytes=%d",
                     call, width, height, level, internal, bytes);
    if (driver_pvrtc == 0 && real_tex_image &&
        internal >= PVRTC_RGB_4BPP && internal <= PVRTC_RGBA_2BPP &&
        target == GL_TEXTURE_2D && level >= 0 && border == 0) {
        int result;
        unsigned char *rgba = decode_pvrtc_image(internal, width, height, bytes, pixels, &result);
        if (rgba) {
            if (fallback_uploads < 8 && log_graphics)
                log_graphics(ANDROID_LOG_INFO, "PVRTC driver upload begin #%u driver=%p", fallback_uploads, (void *)real_tex_image);
            real_tex_image(target, level, GL_RGBA, width, height, 0,
                           GL_RGBA, GL_UNSIGNED_BYTE, rgba);
            free(rgba);
            if (fallback_uploads++ < 32 && log_graphics)
                log_graphics(ANDROID_LOG_INFO, "GL PVRTC software upload %dx%d level=%d format=0x%x",
                             width, height, level, internal);
            if (call < 1024) observe_errors("PVRTC decoded glTexImage2D");
            return;
        }
        record_decode_failure(result, width, height, internal, bytes);
    }
    real_compressed_image(target, level, internal, width, height, border, bytes, pixels);
    if (call < 1024) observe_errors("glCompressedTexImage2D");
}

static void diagnosed_compressed_sub_image(GLenum target, GLint level, GLint x, GLint y,
        GLsizei width, GLsizei height, GLenum format, GLsizei bytes, const void *pixels) {
    describe_context();
    unsigned call = texture_calls++;
    /* PVRTC1 permits reloading a complete image, never a discrete compressed
     * rectangle. The game's full-image reloads use zero offsets. Preserve the
     * original path for nonzero offsets or unsupported formats. */
    if (driver_pvrtc == 0 && real_tex_sub_image &&
        format >= PVRTC_RGB_4BPP && format <= PVRTC_RGBA_2BPP &&
        target == GL_TEXTURE_2D && level >= 0 && x == 0 && y == 0) {
        int result;
        unsigned char *rgba = decode_pvrtc_image(format, width, height, bytes, pixels, &result);
        if (rgba) {
            if (fallback_uploads < 8 && log_graphics)
                log_graphics(ANDROID_LOG_INFO, "PVRTC driver subimage begin #%u driver=%p", fallback_uploads, (void *)real_tex_sub_image);
            real_tex_sub_image(target, level, 0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
            free(rgba);
            if (fallback_uploads++ < 32 && log_graphics)
                log_graphics(ANDROID_LOG_INFO, "GL PVRTC software full-image update %dx%d level=%d format=0x%x",
                             width, height, level, format);
            if (call < 1024) observe_errors("PVRTC decoded glTexSubImage2D");
            return;
        }
        record_decode_failure(result, width, height, format, bytes);
    }
    real_compressed_sub_image(target, level, x, y, width, height, format, bytes, pixels);
    if (call < 1024) observe_errors("glCompressedTexSubImage2D");
}

static void diagnosed_tex_sub_image(GLenum target, GLint level, GLint x, GLint y,
                                    GLsizei width, GLsizei height, GLenum format,
                                    GLenum type, const void *pixels) {
    real_tex_sub_image(target, level, x, y, width, height, format, type, pixels);
    if (texture_calls++ < 1024) observe_errors("glTexSubImage2D");
}

static void diagnosed_draw_arrays(GLenum mode, GLint first, GLsizei count) {
    real_draw_arrays(mode, first, count);
    if (draw_calls++ < 24) observe_errors("glDrawArrays");
}
static void diagnosed_draw_elements(GLenum mode, GLsizei count, GLenum type, const void *indices) {
    real_draw_elements(mode, count, type, indices);
    if (draw_calls++ < 24) observe_errors("glDrawElements");
}
static void diagnosed_alpha_func(GLenum function, GLclampf reference) {
    if (alpha_calls++ < 8 && log_graphics)
        log_graphics(ANDROID_LOG_INFO, "GL AlphaFunc func=0x%x reference=%f", function, (double)reference);
    real_alpha_func(function, reference);
}
static void diagnosed_alpha_funcx(GLenum function, GLclampx reference) {
    if (alpha_calls++ < 8 && log_graphics)
        log_graphics(ANDROID_LOG_INFO, "GL AlphaFuncx func=0x%x reference=%d", function, reference);
    real_alpha_funcx(function, reference);
}
static void diagnosed_blend_func(GLenum source, GLenum destination) {
    if (blend_calls++ < 8 && log_graphics)
        log_graphics(ANDROID_LOG_INFO, "GL BlendFunc source=0x%x destination=0x%x", source, destination);
    real_blend_func(source, destination);
}

static void *diagnosed_get_proc(const char *name) {
    void *actual = real_get_proc(name);
    return s3ce_graphics_symbol(NULL, name, actual, log_graphics);
}

void *s3ce_graphics_symbol(void *handle, const char *name, void *actual,
                          s3ce_graphics_log logger) {
    if (!actual || !name) return actual;
    log_graphics = logger;
    if (!strcmp(name, "eglGetProcAddress")) {
        real_get_proc = (void *(*)(const char *))actual;
        return (void *)(uintptr_t)&diagnosed_get_proc;
    }
    if (name[0] != 'g' || name[1] != 'l') return actual;
    if (!real_get_string) real_get_string = dlsym(handle ? handle : RTLD_DEFAULT, "glGetString");
    if (!real_get_error) real_get_error = dlsym(handle ? handle : RTLD_DEFAULT, "glGetError");
    if (!real_tex_image) real_tex_image = dlsym(handle ? handle : RTLD_DEFAULT, "glTexImage2D");
    if (!real_tex_sub_image) real_tex_sub_image = dlsym(handle ? handle : RTLD_DEFAULT, "glTexSubImage2D");
    if (real_get_proc) {
        if (!real_get_string) real_get_string = real_get_proc("glGetString");
        if (!real_get_error) real_get_error = real_get_proc("glGetError");
        if (!real_tex_image) real_tex_image = real_get_proc("glTexImage2D");
        if (!real_tex_sub_image) real_tex_sub_image = real_get_proc("glTexSubImage2D");
    }
#define WRAP(symbol, pointer, wrapper) \
    if (!strcmp(name, symbol)) { pointer = (__typeof__(pointer))actual; return (void *)(uintptr_t)&wrapper; }
    WRAP("glGetString", real_get_string, diagnosed_get_string)
    WRAP("glGetError", real_get_error, diagnosed_get_error)
    WRAP("glTexImage2D", real_tex_image, diagnosed_tex_image)
    WRAP("glCompressedTexImage2D", real_compressed_image, diagnosed_compressed_image)
    WRAP("glCompressedTexSubImage2D", real_compressed_sub_image, diagnosed_compressed_sub_image)
    WRAP("glTexSubImage2D", real_tex_sub_image, diagnosed_tex_sub_image)
    WRAP("glDrawArrays", real_draw_arrays, diagnosed_draw_arrays)
    WRAP("glDrawElements", real_draw_elements, diagnosed_draw_elements)
    WRAP("glAlphaFunc", real_alpha_func, diagnosed_alpha_func)
    WRAP("glAlphaFuncx", real_alpha_funcx, diagnosed_alpha_funcx)
    WRAP("glBlendFunc", real_blend_func, diagnosed_blend_func)
#undef WRAP
    return actual;
}
