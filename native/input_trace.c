#include "input_trace.h"
#include <stdatomic.h>
#include <limits.h>
#include <time.h>

enum { TRACE_LIMIT = 256, LOG_INFO = 4 };
static s3ce_input_motion original_motion;
static const uint8_t *pointer_state;
static s3ce_input_log input_logger;
static atomic_uint event_count;
static atomic_uint down_count, move_count, up_count, other_count, boundary_count;

static unsigned increment(atomic_uint *counter) {
    unsigned previous = atomic_load_explicit(counter, memory_order_relaxed);
    while (previous != UINT_MAX && !atomic_compare_exchange_weak_explicit(
            counter, &previous, previous + 1, memory_order_relaxed, memory_order_relaxed)) {}
    return previous == UINT_MAX ? UINT_MAX : previous + 1;
}

struct sample {
    uint32_t primary;
    int32_t published_x, published_y;
    int16_t pending_x, pending_y;
    unsigned current_button, pending_button;
};

static struct sample sample_state(void) {
    struct sample state = {0};
    if (!pointer_state) return state;
    /* Source globals are naturally aligned. Volatile accesses avoid treating
     * these changing foreign-runtime globals as constants across the JNI call. */
    const volatile uint8_t *p = pointer_state;
    state.current_button = p[0];
    state.pending_button = p[5];
    state.published_x = *(const volatile int32_t *)(p + 0x0c);
    state.published_y = *(const volatile int32_t *)(p + 0x10);
    state.pending_x = *(const volatile int16_t *)(p + 0x14);
    state.pending_y = *(const volatile int16_t *)(p + 0x16);
    state.primary = *(const volatile uint32_t *)(p + 0x24);
    return state;
}

static long long monotonic_ms(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now)) return -1;
    return (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static void trace_motion(JNIEnv *env, jobject view, jint id, jint type, jint x, jint y) {
    unsigned event = increment(&event_count);
    int boundary = type == 1 || type == 2 || type == 4 || type == 5;
    if (type == 1 || type == 4) increment(&down_count);
    else if (type == 2 || type == 5) increment(&up_count);
    else if (type == 3 || type == 6) increment(&move_count);
    else increment(&other_count);
    unsigned later_boundary = event > TRACE_LIMIT && boundary ? increment(&boundary_count) : 0;
    int aggregate = later_boundary && (later_boundary <= 32
            || !(later_boundary & (later_boundary - 1)));
    int trace = input_logger && (event <= TRACE_LIMIT || aggregate);
    struct sample before = {0};
    if (trace) before = sample_state();
    original_motion(env, view, id, type, x, y);
    if (trace) {
        struct sample after = sample_state();
        input_logger(LOG_INFO,
                "Input JNI %s #%u timeMs=%lld id=%d type=%d xy=%d,%d primary=%u->%u "
                "pending=%d,%d/%u->%d,%d/%u published=%d,%d/%u->%d,%d/%u "
                "totals down=%u move=%u up=%u other=%u state=%s",
                aggregate ? "SUMMARY" : "event", event, monotonic_ms(), id, type, x, y,
                before.primary, after.primary,
                before.pending_x, before.pending_y, before.pending_button,
                after.pending_x, after.pending_y, after.pending_button,
                before.published_x, before.published_y, before.current_button,
                after.published_x, after.published_y, after.current_button,
                atomic_load_explicit(&down_count, memory_order_relaxed),
                atomic_load_explicit(&move_count, memory_order_relaxed),
                atomic_load_explicit(&up_count, memory_order_relaxed),
                atomic_load_explicit(&other_count, memory_order_relaxed),
                pointer_state ? "sample" : "unavailable");
    }
}

s3ce_input_motion s3ce_input_trace_prepare(s3ce_input_motion original,
                                         const uint8_t *pointer_globals,
                                         s3ce_input_log logger) {
    if (!original) return NULL;
    original_motion = original;
    pointer_state = pointer_globals;
    input_logger = logger;
    atomic_store_explicit(&event_count, 0, memory_order_relaxed);
    atomic_store_explicit(&down_count, 0, memory_order_relaxed);
    atomic_store_explicit(&move_count, 0, memory_order_relaxed);
    atomic_store_explicit(&up_count, 0, memory_order_relaxed);
    atomic_store_explicit(&other_count, 0, memory_order_relaxed);
    atomic_store_explicit(&boundary_count, 0, memory_order_relaxed);
    return trace_motion;
}
