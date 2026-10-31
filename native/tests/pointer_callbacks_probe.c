/* Freestanding harness: production proxy module plus original gateway pointers. */
#include "../pointer_callbacks.h"
#include <pthread.h>
#include <time.h>

uintptr_t probe_legacy_base;
volatile unsigned probe_logs, probe_invocations, probe_observations;
volatile unsigned probe_generation_failure;
volatile unsigned probe_original_calls[17];
typedef int32_t (*register_api)(int, s3ce_pointer_callback, void *);
typedef int32_t (*unregister_api)(int, s3ce_pointer_callback);
register_api probe_register_api;
unregister_api probe_unregister_api;

#define ORIGINALS(X) X(0) X(1) X(2) X(3) X(4) X(5) X(6) X(7) X(8) \
                     X(9) X(10) X(11) X(12) X(13) X(14) X(15) X(16)
#define DEFINE_ORIGINAL(index) \
    static int32_t original_##index(void *system, void *user) { \
        (void)system; (void)user; ++probe_original_calls[index]; return -100 + index; \
    }
ORIGINALS(DEFINE_ORIGINAL)
#define ORIGINAL_ADDRESS(index) original_##index,
s3ce_pointer_callback const probe_originals[] = { ORIGINALS(ORIGINAL_ADDRESS) };

int32_t probe_reentrant(void *system, void *user) {
    (void)system;
    if (probe_unregister_api(1, probe_reentrant) ||
        probe_register_api(1, original_1, user)) return -78;
    return -77;
}

int pthread_mutex_lock(pthread_mutex_t *lock) { (void)lock; return 0; }
int pthread_mutex_unlock(pthread_mutex_t *lock) { (void)lock; return 0; }
int clock_gettime(clockid_t clock, struct timespec *now) {
    (void)clock; now->tv_sec = 1; now->tv_nsec = 1000000; return 0;
}
void *memcpy(void *destination, const void *source, size_t size) {
    unsigned char *out = destination;
    const unsigned char *in = source;
    for (size_t i = 0; i < size; ++i) out[i] = in[i];
    return destination;
}
void *memset(void *destination, int value, size_t size) {
    unsigned char *out = destination;
    for (size_t i = 0; i < size; ++i) out[i] = (unsigned char)value;
    return destination;
}
void __aeabi_memcpy8(void *destination, const void *source, size_t size) {
    memcpy(destination, source, size);
}
uintptr_t __stack_chk_guard = 0x6ac79351u;
__attribute__((noreturn)) void __stack_chk_fail(void) { for (;;) {} }

static void log_message(int priority, const char *format, ...) {
    (void)priority; (void)format; ++probe_logs;
}
static s3ce_pointer_callback create_proxy(s3ce_pointer_callback proxy) {
    if (probe_generation_failure) return NULL;
    typedef s3ce_pointer_callback (*generator)(s3ce_pointer_callback, unsigned, unsigned);
    return ((generator)(probe_legacy_base + 0x3c9a1))(proxy, 4, 0);
}
int32_t probe_invoke(s3ce_pointer_callback callback, void *system, void *user) {
    ++probe_invocations;
    typedef int32_t (*gateway)(s3ce_pointer_callback, void *, void *,
                              uintptr_t, uintptr_t, uintptr_t, uintptr_t, uintptr_t);
    return ((gateway)(probe_legacy_base + 0x3c558))(callback, system, user, 0, 0, 0, 0, 0);
}
static void observe(int event, s3ce_pointer_callback original, char *text, size_t size) {
    (void)event; (void)original; ++probe_observations;
    if (size) text[0] = 0;
}
void probe_bind(uintptr_t legacy_base) {
    probe_legacy_base = legacy_base;
    s3ce_pointer_callbacks_bind(
        (s3ce_pointer_core_register)(legacy_base + 0x26edd),
        (s3ce_pointer_core_unregister)(legacy_base + 0x27525),
        create_proxy, probe_invoke, observe, log_message);
}
