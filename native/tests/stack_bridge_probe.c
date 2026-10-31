/* Freestanding ARM32 harness for the production stack bridge. No game assets. */
#define _GNU_SOURCE
#include "../stack_bridge.h"
#include <pthread.h>
#include <stdint.h>
#include <stddef.h>

#define LEGACY_BASE 0x10000000u
#define OS_LOW 0xd0000000u
#define OS_SIZE 0x00100000u
#define LOADER_SLOT ((const uintptr_t *)(LEGACY_BASE + 0x56758u))
#define GATEWAY ((void (*)(void))(LEGACY_BASE + 0x3c7f0u))
#define FIBRE_FLAG (*(volatile unsigned char *)(LEGACY_BASE + 0x54b68u + 0x0cu))

volatile unsigned probe_managed_entries;
volatile unsigned probe_stack_errors;
volatile unsigned probe_work_entries;
volatile unsigned probe_nested_entries;
volatile unsigned probe_canary_errors;
volatile unsigned probe_log_calls;
volatile unsigned probe_do_nested;
volatile unsigned probe_pthread_self_calls;
volatile unsigned probe_flip_thread;
volatile uintptr_t probe_raw_sp;
volatile uintptr_t probe_outer_sp;
volatile uintptr_t probe_nested_sp;
volatile uintptr_t probe_nested_before;
volatile uintptr_t probe_nested_after;
volatile unsigned probe_outer_flag;
volatile unsigned probe_nested_flag;
volatile int probe_nested_status;

/* Production module uses the public pthread APIs; the emulator models one
 * Android thread and its registered 1 MiB native stack through these mocks. */
pthread_t pthread_self(void) {
    ++probe_pthread_self_calls;
    return (pthread_t)((probe_flip_thread && probe_pthread_self_calls > 1) ? 0x5678u : 0x1234u);
}
int pthread_equal(pthread_t first, pthread_t second) { return first == second; }
int pthread_getattr_np(pthread_t thread, pthread_attr_t *attributes) {
    (void)thread; (void)attributes; return 0;
}
int pthread_attr_getstack(const pthread_attr_t *attributes, void **base, size_t *size) {
    (void)attributes; *base = (void *)OS_LOW; *size = OS_SIZE; return 0;
}
int pthread_attr_getguardsize(const pthread_attr_t *attributes, size_t *size) {
    (void)attributes; *size = 4096; return 0;
}
int pthread_attr_destroy(pthread_attr_t *attributes) { (void)attributes; return 0; }

/* Keep freestanding builds independent of platform libraries. */
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
uintptr_t __stack_chk_guard = 0x6ac79351u;
__attribute__((noreturn)) void __stack_chk_fail(void) { for (;;) {} }

static uintptr_t current_sp(void) {
    uintptr_t value;
    __asm__ volatile("mov %0, sp" : "=r"(value));
    return value;
}
void probe_log(int priority, const char *format, ...) {
    (void)priority; (void)format; ++probe_log_calls;
}
static void clobber_scratch_fp(void) {
#if defined(__ARM_NEON)
    /* JNI/driver work can overwrite every AAPCS caller-saved FP register. */
    __asm__ volatile(
        "veor q0, q0, q0\n\tveor q1, q1, q1\n\tveor q2, q2, q2\n\tveor q3, q3, q3\n\t"
        "veor q8, q8, q8\n\tveor q9, q9, q9\n\tveor q10, q10, q10\n\tveor q11, q11, q11\n\t"
        "veor q12, q12, q12\n\tveor q13, q13, q13\n\tveor q14, q14, q14\n\tveor q15, q15, q15"
        : : : "d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7",
                "d16", "d17", "d18", "d19", "d20", "d21", "d22", "d23",
                "d24", "d25", "d26", "d27", "d28", "d29", "d30", "d31");
#endif
}
static void mock_art_invoke(void) {
    /* AOSP13 reflection.cc rejects a managed call before method entry when
     * its native frame lies below Thread::GetStackEnd(). The mock registered
     * end is OS_LOW; passing here models entry, not Android execution. */
    uintptr_t sp = current_sp();
    if (sp < OS_LOW) { ++probe_stack_errors; return; }
    if (sp >= OS_LOW + OS_SIZE) { ++probe_stack_errors; return; }
    ++probe_managed_entries;
}
void probe_raw_work(void) {
    probe_raw_sp = current_sp();
    mock_art_invoke();
}
static void nested_work(void) {
    volatile uint32_t canary[24];
    for (unsigned i = 0; i < 24; ++i) canary[i] = 0x5ae90000u + i;
    clobber_scratch_fp();
    ++probe_nested_entries;
    probe_nested_sp = current_sp();
    probe_nested_flag = FIBRE_FLAG;
    mock_art_invoke();
    for (unsigned i = 0; i < 24; ++i)
        if (canary[i] != 0x5ae90000u + i) ++probe_canary_errors;
}
void probe_work(void) {
    /* More than the old swap detector's near-stack window: an erroneous nested
     * gateway would rewind live outer frames and destroy these canaries. */
    volatile uint32_t canary[384];
    for (unsigned i = 0; i < 384; ++i) canary[i] = 0x9ac10000u + i;
    clobber_scratch_fp();
    ++probe_work_entries;
    probe_outer_sp = current_sp();
    probe_outer_flag = FIBRE_FLAG;
    mock_art_invoke();
    if (probe_do_nested) {
        probe_nested_before = current_sp();
        probe_nested_status = s3ce_call_on_thread_stack(nested_work, LOADER_SLOT, GATEWAY, probe_log);
        probe_nested_after = current_sp();
    }
    for (unsigned i = 0; i < 384; ++i)
        if (canary[i] != 0x9ac10000u + i) ++probe_canary_errors;
}
