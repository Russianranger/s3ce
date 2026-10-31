#include "pointer_callbacks.h"
#include <limits.h>
#include <pthread.h>
#include <stdatomic.h>
#include <string.h>
#include <time.h>

enum { SLOT_COUNT = 16, FIRST_CALLBACKS = 64, LOG_INFO = 4 };
struct callback_slot {
    _Atomic(s3ce_pointer_callback) original;
    s3ce_pointer_callback generated;
    int event;
    int attempted;
};
static struct callback_slot slots[SLOT_COUNT];
static pthread_mutex_t slot_lock = PTHREAD_MUTEX_INITIALIZER;
static s3ce_pointer_core_register core_register;
static s3ce_pointer_core_unregister core_unregister;
static s3ce_pointer_create_proxy generate_proxy;
static s3ce_pointer_invoke invoke_original;
static s3ce_pointer_observer observe_game;
static s3ce_pointer_log log_message;
static atomic_uint callback_count, boundary_count, registration_count;

static unsigned increment(atomic_uint *counter) {
    unsigned old = atomic_load_explicit(counter, memory_order_relaxed);
    while (old != UINT_MAX && !atomic_compare_exchange_weak_explicit(
            counter, &old, old + 1, memory_order_relaxed, memory_order_relaxed)) {}
    return old == UINT_MAX ? UINT_MAX : old + 1;
}
static int power_of_two(unsigned value) { return value && !(value & (value - 1)); }
static long long monotonic_ms(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now)) return -1;
    return (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static int32_t dispatch_slot(unsigned index, void *system_data, void *user_data) {
    struct callback_slot *slot = &slots[index];
    s3ce_pointer_callback original = atomic_load_explicit(&slot->original, memory_order_acquire);
    int event = slot->event;
    unsigned count = increment(&callback_count);
    unsigned boundary = event == 0 || event == 2 ? increment(&boundary_count) : 0;
    int trace = log_message && (count <= FIRST_CALLBACKS || power_of_two(count)
            || (boundary && (boundary <= 16 || power_of_two(boundary))));
    if (trace) {
        int32_t values[4] = {0};
        size_t size = event == 1 ? 8 : event == 3 ? 12 : 16;
        if (system_data) memcpy(values, system_data, size);
        log_message(LOG_INFO,
            "Pointer callback ENTER #%u timeMs=%lld event=%d original=%p user=%p data=%d,%d,%d,%d valid=%d",
            count, monotonic_ms(), event, (void *)(uintptr_t)original, user_data,
            values[0], values[1], values[2], values[3], system_data != NULL);
    }
    /* Both transitions use the supplied runtime's stack gateways. A raw C call
     * from the OS stack would enter game code with the wrong stack bookkeeping. */
    int32_t result = invoke_original(original, system_data, user_data);
    if (trace) {
        char observed[512] = "observation=unavailable";
        if (observe_game) observe_game(event, original, observed, sizeof(observed));
        observed[sizeof(observed) - 1] = 0;
        log_message(LOG_INFO,
            "Pointer callback EXIT #%u timeMs=%lld event=%d result=%d %s",
            count, monotonic_ms(), event, result, observed);
    }
    return result;
}

#define PROXY_LIST(X) X(0) X(1) X(2) X(3) X(4) X(5) X(6) X(7) \
                      X(8) X(9) X(10) X(11) X(12) X(13) X(14) X(15)
#define DEFINE_PROXY(index) \
    static int32_t proxy_##index(void *system_data, void *user_data) { \
        return dispatch_slot(index, system_data, user_data); \
    }
PROXY_LIST(DEFINE_PROXY)
#undef DEFINE_PROXY
#define PROXY_ADDRESS(index) proxy_##index,
static const s3ce_pointer_callback proxies[SLOT_COUNT] = { PROXY_LIST(PROXY_ADDRESS) };
#undef PROXY_ADDRESS

void s3ce_pointer_callbacks_bind(s3ce_pointer_core_register register_core,
        s3ce_pointer_core_unregister unregister_core,
        s3ce_pointer_create_proxy create_proxy, s3ce_pointer_invoke invoke,
        s3ce_pointer_observer observer, s3ce_pointer_log logger) {
    core_register = register_core;
    core_unregister = unregister_core;
    generate_proxy = create_proxy;
    invoke_original = invoke;
    observe_game = observer;
    log_message = logger;
    for (unsigned i = 0; i < SLOT_COUNT; ++i) {
        atomic_store_explicit(&slots[i].original, NULL, memory_order_relaxed);
        slots[i].generated = NULL;
        slots[i].event = 0;
        slots[i].attempted = 0;
    }
    atomic_store_explicit(&callback_count, 0, memory_order_relaxed);
    atomic_store_explicit(&boundary_count, 0, memory_order_relaxed);
    atomic_store_explicit(&registration_count, 0, memory_order_relaxed);
}

int32_t s3ce_pointer_register_observed(int event, s3ce_pointer_callback callback,
                                     void *user_data) {
    s3ce_pointer_callback registered = callback;
    if (event >= 0 && event < 4 && callback && generate_proxy && invoke_original) {
        pthread_mutex_lock(&slot_lock);
        struct callback_slot *selected = NULL;
        unsigned index = 0;
        for (unsigned i = 0; i < SLOT_COUNT; ++i) {
            s3ce_pointer_callback current = atomic_load_explicit(&slots[i].original, memory_order_acquire);
            if (current == callback && slots[i].event == event) {
                selected = &slots[i]; index = i; break;
            }
            if (!selected && !current) { selected = &slots[i]; index = i; }
        }
        if (selected) {
            if (!atomic_load_explicit(&selected->original, memory_order_relaxed)) {
                selected->event = event;
                atomic_store_explicit(&selected->original, callback, memory_order_release);
            }
            /* A failed generation remains pass-through forever, even if a
             * later attempt could succeed. Changing its identity would turn
             * an original duplicate registration into a second callback. */
            if (!selected->attempted) {
                selected->attempted = 1;
                selected->generated = generate_proxy(proxies[index]);
            }
            if (selected->generated) registered = selected->generated;
        }
        pthread_mutex_unlock(&slot_lock);
    }
    int32_t result = core_register(6, 4, event, registered, user_data, 0);
    unsigned count = increment(&registration_count);
    if (log_message && (count <= 64 || power_of_two(count)))
        log_message(LOG_INFO, "Pointer REGISTER #%u event=%d original=%p registered=%p user=%p result=%d observed=%d",
            count, event, (void *)(uintptr_t)callback, (void *)(uintptr_t)registered,
            user_data, result, registered != callback);
    return result;
}

int32_t s3ce_pointer_unregister_observed(int event, s3ce_pointer_callback callback) {
    s3ce_pointer_callback registered = callback;
    if (callback) {
        pthread_mutex_lock(&slot_lock);
        for (unsigned i = 0; i < SLOT_COUNT; ++i)
            if (atomic_load_explicit(&slots[i].original, memory_order_acquire) == callback
                    && slots[i].event == event && slots[i].generated) {
                registered = slots[i].generated;
                break;
            }
        pthread_mutex_unlock(&slot_lock);
    }
    int32_t result = core_unregister(6, 4, event, registered, NULL);
    unsigned count = increment(&registration_count);
    if (log_message && (count <= 64 || power_of_two(count)))
        log_message(LOG_INFO, "Pointer UNREGISTER #%u event=%d original=%p registered=%p result=%d",
            count, event, (void *)(uintptr_t)callback, (void *)(uintptr_t)registered, result);
    return result;
}
