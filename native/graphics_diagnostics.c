/* Bounded diagnostics and conditional software PVRTC1 texture compatibility.
 * Other formats and native-capable drivers retain their original upload path.
 * Error flags consumed for diagnosis are returned by the wrapped glGetError.
 */
#include "graphics_diagnostics.h"
#include "pvrtc/pvrtc_bridge.h"
#include <GLES/gl.h>
#include <android/log.h>
#include <dlfcn.h>
#include <limits.h>
#include <math.h>
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
static void (*real_get_integer)(GLenum, GLint *);
static void (*real_get_float)(GLenum, float *);
static void (*real_get_tex_parameter)(GLenum, GLenum, GLint *);
static unsigned char (*real_is_enabled)(GLenum);
static void *(*real_current_context)(void);
static _Thread_local GLenum pending_errors[16];
static _Thread_local unsigned pending_count;
static unsigned texture_calls, draw_calls, alpha_calls, blend_calls, logged_errors;
static unsigned context_logged;
static int driver_pvrtc = -1;
static char software_extensions[32768];
static unsigned fallback_uploads, fallback_failures, fallback_attempts, string_calls;
static unsigned ui_draw_calls;
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

static unsigned observe_errors(const char *operation) {
    unsigned observed = 0;
    if (!real_get_error) return 0;
    /* GL has a finite set of flags. Bound draining in case of a broken driver. */
    for (unsigned i = 0; i < 16; ++i) {
        GLenum error = real_get_error();
        if (error == GL_NO_ERROR) break;
        ++observed;
        remember_error(error);
        if (logged_errors++ < 48 && log_graphics)
            log_graphics(ANDROID_LOG_ERROR, "GL error after %s: 0x%x", operation, error);
    }
    return observed;
}

/* Read-only witness for the four-vertex UI strip path. Sample the first eight
 * draws and powers of two through 2^20, at most 25 snapshots per process.
 * Never change texture units, matrix mode, enables, bindings, or array state.
 * Client pointers and index payloads are deliberately not dereferenced.
 */
static void observe_ui_draw(const char *api, GLenum mode, GLint first,
                            GLsizei count, GLenum type) {
    if (mode != 5 || count != 4 || first != 0 ||
        (type != 0 && type != 0x1403)) return;
    if (ui_draw_calls != UINT_MAX) ++ui_draw_calls;
    unsigned call = ui_draw_calls;
    if (call > 8 && (call > (1u << 20) || (call & (call - 1)))) return;
    if (!log_graphics || !real_current_context || !real_current_context() ||
        !real_get_integer || !real_get_float || !real_get_tex_parameter ||
        !real_is_enabled || !real_get_error) return;
    /* Preserve pre-existing flags separately from any query-generated error. */
    observe_errors("before UI draw state queries");
    GLint active = INT_MIN, client = INT_MIN, binding = INT_MIN, min = INT_MIN;
    GLint vertex = INT_MIN, uv = INT_MIN, colors = INT_MIN, matrix_mode = INT_MIN;
    GLint viewport[4] = {INT_MIN, INT_MIN, INT_MIN, INT_MIN};
    float color[4] = {NAN, NAN, NAN, NAN};
    float projection[16], modelview[16], texture[16];
    for (unsigned i = 0; i < 16; ++i)
        projection[i] = modelview[i] = texture[i] = NAN;
    real_get_integer(0x84e0, &active);  /* GL_ACTIVE_TEXTURE */
    real_get_integer(0x84e1, &client);  /* GL_CLIENT_ACTIVE_TEXTURE */
    real_get_integer(0x8069, &binding); /* GL_TEXTURE_BINDING_2D */
    real_get_integer(0x8074, &vertex);  /* GL_VERTEX_ARRAY */
    real_get_integer(0x8078, &uv);      /* GL_TEXTURE_COORD_ARRAY */
    real_get_integer(0x8076, &colors);  /* GL_COLOR_ARRAY */
    real_get_integer(0x0ba0, &matrix_mode);
    real_get_integer(0x0ba2, viewport);
    real_get_tex_parameter(GL_TEXTURE_2D, 0x2801, &min);
    unsigned enabled = (real_is_enabled(GL_TEXTURE_2D) ? 1u : 0u) |
        (real_is_enabled(0x0be2) ? 2u : 0u) | /* blend */
        (real_is_enabled(0x0bc0) ? 4u : 0u) | /* alpha test */
        (real_is_enabled(0x0b71) ? 8u : 0u) | /* depth test */
        (real_is_enabled(0x0b44) ? 16u : 0u); /* cull face */
    real_get_float(0x0b00, color);
    real_get_float(0x0ba7, projection);
    real_get_float(0x0ba6, modelview);
    real_get_float(0x0ba8, texture);
    unsigned errors = observe_errors("UI draw state queries");
    log_graphics(ANDROID_LOG_INFO,
        "UI GPU #%u %s active=%x client=%x tex=%d min=%x arrays=%d/%d/%d caps=%x mode=%x viewport=%d,%d,%d,%d color=%g,%g,%g,%g queryErrors=%u",
        call, api, (unsigned)active, (unsigned)client, binding, (unsigned)min,
        vertex, uv, colors, enabled, (unsigned)matrix_mode, viewport[0],
        viewport[1], viewport[2], viewport[3], (double)color[0],
        (double)color[1], (double)color[2], (double)color[3], errors);
    const float *matrices[] = {projection, modelview, texture};
    const char *names[] = {"projection", "modelview", "texture"};
    for (unsigned i = 0; i < 3; ++i) {
        const float *m = matrices[i];
        log_graphics(ANDROID_LOG_INFO,
            "UI GPU #%u %s=%g,%g,%g,%g;%g,%g,%g,%g;%g,%g,%g,%g;%g,%g,%g,%g",
            call, names[i], (double)m[0], (double)m[1], (double)m[2],
            (double)m[3], (double)m[4], (double)m[5], (double)m[6],
            (double)m[7], (double)m[8], (double)m[9], (double)m[10],
            (double)m[11], (double)m[12], (double)m[13], (double)m[14],
            (double)m[15]);
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
    observe_ui_draw("DrawArrays", mode, first, count, 0);
    real_draw_arrays(mode, first, count);
    if (draw_calls++ < 24) observe_errors("glDrawArrays");
}
static void diagnosed_draw_elements(GLenum mode, GLsizei count, GLenum type, const void *indices) {
    observe_ui_draw("DrawElements", mode, 0, count, type);
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
    if (!real_get_integer) real_get_integer = dlsym(handle ? handle : RTLD_DEFAULT, "glGetIntegerv");
    if (!real_get_float) real_get_float = dlsym(handle ? handle : RTLD_DEFAULT, "glGetFloatv");
    if (!real_get_tex_parameter) real_get_tex_parameter = dlsym(handle ? handle : RTLD_DEFAULT, "glGetTexParameteriv");
    if (!real_is_enabled) real_is_enabled = dlsym(handle ? handle : RTLD_DEFAULT, "glIsEnabled");
    if (!real_current_context) real_current_context = dlsym(RTLD_DEFAULT, "eglGetCurrentContext");
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
