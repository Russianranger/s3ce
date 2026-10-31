#include "../input_trace.h"
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static _Alignas(4) uint8_t globals[48];
static unsigned calls, messages;
static char last_message[1024];
static JNIEnv *expected_env;
static jobject expected_view;
static jint expected_id, expected_type, expected_x, expected_y;

static void logger(int priority, const char *format, ...) {
    assert(priority == 4);
    char message[1024];
    va_list args;
    va_start(args, format);
    vsnprintf(message, sizeof(message), format, args);
    va_end(args);
    strcpy(last_message, message);
    ++messages;
}

static void original(JNIEnv *env, jobject view, jint id, jint type, jint x, jint y) {
    assert(env == expected_env && view == expected_view);
    assert(id == expected_id && type == expected_type);
    assert(x == expected_x && y == expected_y);
    ++calls;
    uint32_t primary = 8;
    int16_t px = 1300, py = 580;
    memcpy(globals + 0x24, &primary, sizeof(primary));
    memcpy(globals + 0x14, &px, sizeof(px));
    memcpy(globals + 0x16, &py, sizeof(py));
    globals[5] = 1;
}

int main(void) {
    /* An invalid JNI vtable pointer proves the wrapper calls no JNI functions. */
    expected_env = (JNIEnv *)(uintptr_t)0x1;
    expected_view = (jobject)(uintptr_t)0x12345678;
    expected_id = 7; expected_type = 6; expected_x = 1300; expected_y = 580;
    assert(!s3ce_input_trace_prepare(NULL, globals, logger));
    s3ce_input_motion wrapped = s3ce_input_trace_prepare(original, globals, logger);
    wrapped(expected_env, expected_view, expected_id, expected_type, expected_x, expected_y);
    assert(calls == 1 && messages == 1);
    assert(strstr(last_message, "#1") && strstr(last_message, "id=7 type=6 xy=1300,580"));
    assert(strstr(last_message, "primary=0->8 pending=0,0/0->1300,580/1"));
    for (unsigned i = 1; i < 1024; ++i)
        wrapped(expected_env, expected_view, expected_id, expected_type, expected_x, expected_y);
    assert(calls == 1024 && messages == 256);
    expected_type = 5;
    for (unsigned i = 0; i < 128; ++i)
        wrapped(expected_env, expected_view, expected_id, expected_type, expected_x, expected_y);
    assert(calls == 1152 && messages == 256 + 32 + 2);  // boundary64 and128 remain visible
    assert(strstr(last_message, "SUMMARY #1152") && strstr(last_message, "move=1024 up=128"));

    wrapped = s3ce_input_trace_prepare(original, NULL, NULL);
    wrapped(expected_env, expected_view, expected_id, expected_type, expected_x, expected_y);
    assert(calls == 1153 && messages == 290);
    wrapped = s3ce_input_trace_prepare(original, NULL, logger);
    expected_id = -1; expected_type = 0; expected_x = -100; expected_y = 32768;
    wrapped(expected_env, expected_view, expected_id, expected_type, expected_x, expected_y);
    assert(calls == 1154 && messages == 291);
    assert(strstr(last_message, "id=-1 type=0 xy=-100,32768"));
    assert(strstr(last_message, "state=unavailable"));
    puts("PASS bounded native input trace preserves every call/argument and uses no JNI");
    return 0;
}
