#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "../graphics_diagnostics.c"

static unsigned logs, calls, error_reads, compressed_calls, sub_calls, compressed_sub_calls;
static GLsizei expected_width = 8, expected_height = 8;
static GLint expected_level;
static int fallback_mode;
static unsigned char first_pixel[4];
static GLenum next_error;
static const void *received_pixels;
static GLenum test_error(void);
static unsigned ui_logs, ui_queries, array_draws, element_draws;
static int ui_context = 1, ui_query_failure;
static GLenum expected_mode = 5, expected_type = 0x1403;
static GLint expected_first;
static GLsizei expected_count = 4;
static const void *expected_indices;
static void *test_current(void) { return ui_context ? (void *)(uintptr_t)1 : NULL; }
static void ui_log(int priority, const char *format, ...) {
    (void)priority;
    if (!strncmp(format, "UI GPU", 6)) ++ui_logs;
}
static void test_integer(GLenum name, GLint *value) {
    ++ui_queries;
    if (ui_query_failure) { next_error = GL_INVALID_ENUM; return; }
    if (name == 0xba2) {
        const GLint viewport[] = {0, 0, 1920, 1080};
        memcpy(value, viewport, sizeof(viewport));
    } else {
        assert(name == 0x84e0 || name == 0x84e1 || name == 0x8069 ||
               name == 0x8074 || name == 0x8078 || name == 0x8076 || name == 0xba0);
        *value = name == 0x84e0 || name == 0x84e1 ? 0x84c0 : 1;
    }
}
static void test_float(GLenum name, float *value) {
    ++ui_queries;
    if (ui_query_failure) { next_error = GL_INVALID_ENUM; return; }
    assert(name == 0xb00 || name == 0xba7 || name == 0xba6 || name == 0xba8);
    unsigned size = name == 0xb00 ? 4 : 16;
    for (unsigned i = 0; i < size; ++i) value[i] = size == 4 || i % 5 == 0 ? 1 : 0;
}
static void test_tex_parameter(GLenum target, GLenum name, GLint *value) {
    ++ui_queries;
    assert(target == GL_TEXTURE_2D && name == 0x2801);
    if (ui_query_failure) { next_error = GL_INVALID_ENUM; return; }
    *value = 0x2701;
}
static unsigned char test_enabled(GLenum name) {
    ++ui_queries;
    assert(name == GL_TEXTURE_2D || name == 0xbe2 || name == 0xbc0 ||
           name == 0xb71 || name == 0xb44);
    if (ui_query_failure) next_error = GL_INVALID_ENUM;
    return name == GL_TEXTURE_2D || name == 0xbe2;
}
static void test_array_draw(GLenum mode, GLint first, GLsizei count) {
    assert(mode == expected_mode && first == expected_first && count == expected_count);
    ++array_draws;
}
static void test_element_draw(GLenum mode, GLsizei count, GLenum type, const void *indices) {
    assert(mode == expected_mode && count == expected_count && type == expected_type);
    assert(indices == expected_indices);
    ++element_draws;
}

static void test_ui_state(void) {
    real_current_context = test_current;
    real_get_integer = test_integer;
    real_get_float = test_float;
    real_get_tex_parameter = test_tex_parameter;
    real_is_enabled = test_enabled;
    real_draw_arrays = test_array_draw;
    real_draw_elements = test_element_draw;
    real_get_error = test_error;
    log_graphics = ui_log;
    ui_draw_calls = draw_calls = 0;
    while (diagnosed_get_error() != GL_NO_ERROR) {}
    /* A failed/no-context diagnostic must never prevent or repeat the draw. */
    ui_context = 0;
    diagnosed_draw_arrays(5, 0, 4);
    assert(array_draws == 1 && ui_queries == 0 && ui_logs == 0);
    ui_context = 1;
    real_get_float = NULL;
    diagnosed_draw_arrays(5, 0, 4);
    assert(array_draws == 2 && ui_queries == 0);
    real_get_float = test_float;
    real_get_error = NULL;
    diagnosed_draw_arrays(5, 0, 4);
    assert(array_draws == 3 && ui_queries == 0);
    real_get_error = test_error;
    ui_draw_calls = 0;
    diagnosed_draw_arrays(5, 0, 4);
    assert(array_draws == 4 && ui_logs == 4 && ui_queries == 18);
    /* Observe an existing app flag plus a query failure without losing either. */
    next_error = GL_INVALID_VALUE;
    ui_query_failure = 1;
    expected_indices = (const void *)(uintptr_t)1; /* Must never be dereferenced. */
    diagnosed_draw_elements(5, 4, 0x1403, expected_indices);
    assert(element_draws == 1 && ui_logs == 8);
    assert(diagnosed_get_error() == GL_INVALID_VALUE);
    assert(diagnosed_get_error() == GL_INVALID_ENUM);
    assert(diagnosed_get_error() == GL_NO_ERROR);
    ui_query_failure = 0;
    /* Non-UI topology, start, count and index type get no state queries. */
    unsigned before = ui_queries;
    expected_first = 1;
    diagnosed_draw_arrays(5, 1, 4);
    expected_first = 0; expected_mode = 4;
    diagnosed_draw_arrays(4, 0, 4);
    expected_mode = 5; expected_count = 3;
    diagnosed_draw_arrays(5, 0, 3);
    expected_count = 4; expected_type = 0x1401;
    diagnosed_draw_elements(5, 4, 0x1401, expected_indices);
    expected_type = 0x1403;
    assert(ui_queries == before);
    ui_draw_calls = ui_logs = ui_queries = 0;
    for (unsigned i = 0; i < (1u << 20) + 1; ++i) diagnosed_draw_arrays(5, 0, 4);
    assert(ui_logs == 25 * 4 && ui_queries == 25 * 18);
    ui_draw_calls = UINT_MAX - 1;
    before = ui_queries;
    diagnosed_draw_arrays(5, 0, 4);
    diagnosed_draw_arrays(5, 0, 4);
    assert(ui_draw_calls == UINT_MAX && ui_queries == before);
}
static void test_log(int priority, const char *format, ...) {
    (void)priority; (void)format; ++logs;
}
static const GLubyte *test_string(GLenum name) {
    switch (name) {
        case GL_VERSION: return (const GLubyte *)"OpenGL ES-CM 1.1";
        case GL_VENDOR: return (const GLubyte *)"Test GPU";
        case GL_RENDERER: return (const GLubyte *)"Mock";
        case GL_EXTENSIONS: return (const GLubyte *)"GL_OES_draw_texture GL_OES_texture_npot";
    }
    return NULL;
}
static GLenum test_error(void) {
    ++error_reads;
    GLenum result = next_error;
    next_error = 0;
    return result;
}
static void test_texture(GLenum target, GLint level, GLint internal, GLsizei width,
                         GLsizei height, GLint border, GLenum format, GLenum type,
                         const void *pixels) {
    assert(target == 0xde1 && level == expected_level && internal == 0x1908);
    assert(border == 0 && format == 0x1908 && type == 0x1401);
    assert(fallback_mode ? (width == expected_width && height == expected_height) : (width == 64 && height == 32));
    if (fallback_mode) memcpy(first_pixel, pixels, sizeof(first_pixel));
    received_pixels = pixels;
    ++calls;
}
static void test_compressed(GLenum target, GLint level, GLenum internal,
                             GLsizei width, GLsizei height, GLint border,
                             GLsizei bytes, const void *pixels) {
    (void)target; (void)level; (void)internal; (void)width; (void)height;
    (void)border; (void)bytes; (void)pixels;
    ++compressed_calls;
}
static void test_sub_texture(GLenum target, GLint level, GLint x, GLint y,
        GLsizei width, GLsizei height, GLenum format, GLenum type, const void *pixels) {
    assert(target == GL_TEXTURE_2D && level == expected_level && x == 0 && y == 0);
    assert(width == expected_width && height == expected_height);
    assert(format == GL_RGBA && type == GL_UNSIGNED_BYTE);
    memcpy(first_pixel, pixels, sizeof(first_pixel));
    ++sub_calls;
}
static void test_compressed_sub(GLenum target, GLint level, GLint x, GLint y,
        GLsizei width, GLsizei height, GLenum format, GLsizei bytes, const void *pixels) {
    (void)target; (void)level; (void)x; (void)y; (void)width; (void)height;
    (void)format; (void)bytes; (void)pixels;
    ++compressed_sub_calls;
}
int main(void) {
    real_get_string = test_string;
    real_get_error = test_error;
    real_tex_image = test_texture;
    const GLubyte *(*get_string)(GLenum) = s3ce_graphics_symbol(NULL, "glGetString", test_string, test_log);
    assert(get_string(GL_RENDERER) == test_string(GL_RENDERER));
    assert(context_logged == 1 && logs >= 3);
    assert(strstr((const char *)get_string(GL_EXTENSIONS), PVRTC_EXTENSION));
    assert(!strstr((const char *)test_string(GL_EXTENSIONS), PVRTC_EXTENSION));
    assert(extension_supported("GL_IMG_texture_compression_pvrtc2", PVRTC_EXTENSION) == 0);
    assert(extension_supported("GL_test " PVRTC_EXTENSION " GL_other", PVRTC_EXTENSION) == 1);
    GLenum (*get_error)(void) = s3ce_graphics_symbol(NULL, "glGetError", test_error, test_log);
    void (*texture)(GLenum, GLint, GLint, GLsizei, GLsizei, GLint, GLenum, GLenum, const void *) =
        s3ce_graphics_symbol(NULL, "glTexImage2D", test_texture, test_log);
    unsigned char pixels[64*32*4] = {0};
    next_error = GL_INVALID_ENUM;
    texture(0xde1, 0, 0x1908, 64, 32, 0, 0x1908, 0x1401, pixels);
    assert(calls == 1 && received_pixels == pixels);
    /* Observation consumes the driver flag but preserves it for the game. */
    assert(next_error == 0 && get_error() == GL_INVALID_ENUM && get_error() == 0);
    next_error = GL_INVALID_ENUM;
    texture(0xde1, 0, 0x1908, 64, 32, 0, 0x1908, 0x1401, pixels);
    next_error = GL_INVALID_VALUE;
    texture(0xde1, 0, 0x1908, 64, 32, 0, 0x1908, 0x1401, pixels);
    assert(get_error() == GL_INVALID_ENUM && get_error() == GL_INVALID_VALUE && get_error() == 0);
    unsigned before_logs = logs;
    for (int i = 0; i < 1500; ++i) texture(0xde1, 0, 0x1908, 64, 32, 0, 0x1908, 0x1401, pixels);
    unsigned before_reads = error_reads;
    texture(0xde1, 0, 0x1908, 64, 32, 0, 0x1908, 0x1401, pixels);
    assert(error_reads == before_reads); /* Instrumentation stops after budget. */
    assert(logs - before_logs <= 48);
    assert(s3ce_graphics_symbol(NULL, "unknown", test_texture, test_log) == test_texture);
    assert(s3ce_graphics_symbol(NULL, "glUnknown", NULL, test_log) == NULL);
    fallback_mode = 1;
    texture_calls = 0;
    void (*compressed)(GLenum, GLint, GLenum, GLsizei, GLsizei, GLint, GLsizei, const void *) =
        s3ce_graphics_symbol(NULL, "glCompressedTexImage2D", test_compressed, test_log);
    const uint32_t red[] = {0,0xfc00fc00,0,0xfc00fc00,0,0xfc00fc00,0,0xfc00fc00};
    unsigned before_calls = calls;
    compressed(GL_TEXTURE_2D,0,PVRTC_RGB_4BPP,8,8,0,sizeof(red),red);
    assert(calls == before_calls+1 && compressed_calls == 0);
    assert(first_pixel[0] == 255 && first_pixel[1] == 0 && first_pixel[2] == 0 && first_pixel[3] == 255);
    const uint32_t transparent[8] = {0};
    compressed(GL_TEXTURE_2D,0,PVRTC_RGBA_4BPP,8,8,0,sizeof(transparent),transparent);
    assert(first_pixel[0] == 0 && first_pixel[3] == 0);
    compressed(GL_TEXTURE_2D,0,PVRTC_RGB_4BPP,8,8,0,sizeof(transparent),transparent);
    assert(first_pixel[0] == 0 && first_pixel[3] == 255);
    compressed(GL_TEXTURE_2D,0,PVRTC_RGB_4BPP,8,8,0,sizeof(red)-1,red);
    assert(compressed_calls == 1); /* Invalid compressed data forwarded unchanged. */
    /* Exercise both 2bpp tokens and the final 1x1 mip block. */
    expected_width = 16;
    compressed(GL_TEXTURE_2D,0,PVRTC_RGB_2BPP,16,8,0,sizeof(red),red);
    assert(first_pixel[0] == 255 && first_pixel[3] == 255);
    compressed(GL_TEXTURE_2D,0,PVRTC_RGBA_2BPP,16,8,0,sizeof(transparent),transparent);
    assert(first_pixel[3] == 0);
    expected_width = expected_height = 1;
    expected_level = 7;
    compressed(GL_TEXTURE_2D,7,PVRTC_RGB_4BPP,1,1,0,sizeof(red),red);
    assert(first_pixel[0] == 255);
    /* Full-image compressed updates use the same decoder; invalid offsets or
     * insufficient data preserve the original driver call. */
    real_tex_sub_image = test_sub_texture;
    void (*compressed_sub)(GLenum,GLint,GLint,GLint,GLsizei,GLsizei,GLenum,GLsizei,const void *) =
        s3ce_graphics_symbol(NULL, "glCompressedTexSubImage2D", test_compressed_sub, test_log);
    next_error = GL_INVALID_VALUE;
    compressed_sub(GL_TEXTURE_2D,7,0,0,1,1,PVRTC_RGB_4BPP,sizeof(red),red);
    assert(sub_calls == 1 && compressed_sub_calls == 0 && first_pixel[0] == 255);
    assert(get_error() == GL_INVALID_VALUE && get_error() == 0);
    compressed_sub(GL_TEXTURE_2D,7,0,0,1,1,PVRTC_RGB_4BPP,sizeof(red)-1,red);
    assert(compressed_sub_calls == 1);
    compressed_sub(GL_TEXTURE_2D,7,1,0,1,1,PVRTC_RGB_4BPP,sizeof(red),red);
    assert(compressed_sub_calls == 2);
    expected_width = expected_height = 8;
    expected_level = 0;
    driver_pvrtc = 1;
    compressed(GL_TEXTURE_2D,0,PVRTC_RGB_4BPP,8,8,0,sizeof(red),red);
    assert(compressed_calls == 2); /* Native-capable GPU keeps native path. */
    test_ui_state();
    puts("GL transparency/errors/bounds and conditional PVRTC fallback: PASS");
}
