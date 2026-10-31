#include "../pointer_callbacks.h"
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

struct registration { int event; s3ce_pointer_callback callback; void *user; };
static struct registration records[64];
static unsigned count, generated, invoked, observed, messages;
static int generation_failure;
static void *expected_system;
static void *expected_user;
static unsigned original_calls[17];
static uintptr_t pending_throwable;

static int32_t register_core(int device, int events, int event,
        s3ce_pointer_callback callback, void *user, uint8_t single) {
    assert(device == 6 && events == 4 && single == 0);
    if (!callback || event < 0 || event >= events) return 1;
    for (unsigned i = 0; i < count; ++i)
        if (records[i].event == event && records[i].callback == callback) return 1;
    assert(count < 64);
    records[count++] = (struct registration){event, callback, user};
    return 0;
}
static int32_t unregister_core(int device, int events, int event,
        s3ce_pointer_callback callback, void *specific) {
    assert(device == 6 && events == 4 && specific == NULL);
    int found = 0;
    for (unsigned i = 0; i < count;) {
        if (records[i].event == event && (!callback || records[i].callback == callback)) {
            records[i] = records[--count];
            found = 1;
        } else ++i;
    }
    return found ? 0 : 1;
}
static s3ce_pointer_callback generate(s3ce_pointer_callback proxy) {
    ++generated;
    return generation_failure ? NULL : proxy;
}
static int32_t invoke(s3ce_pointer_callback original, void *system, void *user) {
    ++invoked;
    return original(system, user);
}
static void observe(int event, s3ce_pointer_callback original, char *text, size_t size) {
    assert(event >= 0 && event < 4 && original);
    ++observed;
    snprintf(text, size, "witness=%u", observed);
}
static void logger(int priority, const char *format, ...) {
    assert(priority == 4);
    char buffer[1024];
    va_list args;
    va_start(args, format);
    assert(vsnprintf(buffer, sizeof(buffer), format, args) > 0);
    va_end(args);
    ++messages;
}
#define ORIGINALS(X) X(0) X(1) X(2) X(3) X(4) X(5) X(6) X(7) X(8) \
                     X(9) X(10) X(11) X(12) X(13) X(14) X(15) X(16)
#define DEFINE_ORIGINAL(index) \
    static int32_t original_##index(void *system, void *user) { \
        assert(system == expected_system && user == expected_user); \
        assert(pending_throwable == 0xfeed1234); \
        ++original_calls[index]; \
        return -2000000000 + index; \
    }
ORIGINALS(DEFINE_ORIGINAL)
#define ORIGINAL_ADDRESS(index) original_##index,
static const s3ce_pointer_callback originals[] = { ORIGINALS(ORIGINAL_ADDRESS) };

static void reset(void) {
    count = generated = invoked = observed = messages = 0;
    generation_failure = 0;
    memset(records, 0, sizeof(records));
    memset(original_calls, 0, sizeof(original_calls));
    pending_throwable = 0xfeed1234;
    s3ce_pointer_callbacks_bind(register_core, unregister_core, generate, invoke, observe, logger);
}
static int32_t deliver(unsigned index, void *system) {
    /* Original Notify snapshots each registered row before invoking it. */
    struct registration record = records[index];
    expected_system = system;
    expected_user = record.user;
    int32_t result = record.callback(system, record.user);
    assert(pending_throwable == 0xfeed1234);
    return result;
}
static int32_t reentrant(void *system, void *user) {
    assert(system == expected_system && user == expected_user);
    assert(s3ce_pointer_unregister_observed(0, reentrant) == 0);
    assert(s3ce_pointer_register_observed(1, original_1, user) == 0);
    return -77;
}

int main(void) {
    int32_t payload[4] = {0, 1, 1200, 600};
    reset();
    assert(s3ce_pointer_register_observed(0, original_0, (void *)0x1234) == 0);
    assert(s3ce_pointer_register_observed(0, original_1, (void *)0x5678) == 0);
    assert(records[0].callback != original_0 && records[1].callback != original_1);
    assert(records[0].callback != records[1].callback);
    assert(s3ce_pointer_register_observed(0, original_0, (void *)0x9999) == 1);
    assert(count == 2 && generated == 2 && records[0].user == (void *)0x1234);
    assert(deliver(0, payload) == -2000000000);
    assert(deliver(1, payload) == -1999999999);
    assert(original_calls[0] == 1 && original_calls[1] == 1 && invoked == 2 && observed == 2);
    assert(s3ce_pointer_unregister_observed(0, original_0) == 0);
    assert(s3ce_pointer_unregister_observed(0, original_0) == 1);
    assert(s3ce_pointer_register_observed(0, original_0, (void *)0x8888) == 0);
    assert(generated == 2 && count == 2);  // Never reused or regenerated.
    assert(deliver(1, payload) == -2000000000);
    assert(s3ce_pointer_register_observed(1, original_0, (void *)0x7777) == 0);
    assert(generated == 3);  // Same callback on another event has its own identity.
    assert(s3ce_pointer_register_observed(-1, original_0, NULL) == 1);
    assert(s3ce_pointer_register_observed(4, original_0, NULL) == 1);
    assert(s3ce_pointer_register_observed(0, NULL, NULL) == 1);

    reset();
    generation_failure = 1;
    assert(s3ce_pointer_register_observed(0, original_0, (void *)0x1234) == 0);
    assert(records[0].callback == original_0);
    generation_failure = 0;
    assert(s3ce_pointer_register_observed(0, original_0, (void *)0x9999) == 1);
    assert(generated == 1 && count == 1);  // Permanent fallback preserves duplicates.
    assert(deliver(0, payload) == -2000000000 && invoked == 0 && observed == 0);
    assert(s3ce_pointer_unregister_observed(0, original_0) == 0);

    reset();
    for (unsigned i = 0; i < 17; ++i)
        assert(s3ce_pointer_register_observed(0, originals[i], (void *)(uintptr_t)(i + 1)) == 0);
    assert(generated == 16 && records[16].callback == original_16);
    assert(s3ce_pointer_register_observed(0, original_16, NULL) == 1);
    for (unsigned i = 0; i < 17; ++i) {
        assert(deliver(i, payload) == -2000000000 + (int32_t)i);
        assert(original_calls[i] == 1);
    }
    assert(invoked == 16 && observed == 16);
    assert(s3ce_pointer_unregister_observed(0, NULL) == 0 && count == 0);

    reset();
    assert(s3ce_pointer_register_observed(0, reentrant, (void *)0x5555) == 0);
    assert(deliver(0, payload) == -77);
    assert(count == 1 && records[0].event == 1);
    assert(deliver(0, payload) == -1999999999);
    puts("PASS callback proxies: exact forwarding/returns/cookies, multiple registrations, duplicates, unregister/reentry, permanent failure and bounded pass-through");
}
