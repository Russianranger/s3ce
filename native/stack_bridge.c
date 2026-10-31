#define _GNU_SOURCE
#include "stack_bridge.h"
#include <android/log.h>
#include <pthread.h>
#include <stddef.h>

struct stack_job {
    void (*work)(void);
    uintptr_t low;
    uintptr_t high;
    pthread_t thread;
    s3ce_graphics_log logger;
    int status;
};

static uintptr_t current_sp(void) {
#if defined(__arm__)
    uintptr_t result;
    __asm__ volatile("mov %0, sp" : "=r"(result));
    return result;
#else
    return (uintptr_t)__builtin_frame_address(0);
#endif
}

static void checked_stack_job(void *opaque) {
    struct stack_job *job = opaque;
    uintptr_t sp = current_sp();
    if (sp < job->low || sp >= job->high || !pthread_equal(pthread_self(), job->thread)) {
        if (job->logger) job->logger(ANDROID_LOG_ERROR,
            "Native stack bridge refused callback: SP=%p OS=[%p,%p)",
            (void *)sp, (void *)job->low, (void *)job->high);
        return;
    }
    if (job->logger) job->logger(ANDROID_LOG_INFO,
        "Native stack bridge callback: SP=%p within current pthread stack", (void *)sp);
    job->work();
    job->status = 0;
}

int s3ce_call_on_thread_stack(void (*work)(void), const uintptr_t *loader_sp_slot,
                               void (*gateway)(void), s3ce_graphics_log logger) {
    if (!work) return -1;
    pthread_t thread = pthread_self();
    pthread_attr_t attributes;
    if (pthread_getattr_np(thread, &attributes)) {
        if (logger) logger(ANDROID_LOG_ERROR, "Native stack bridge could not query current pthread");
        return -1;
    }
    void *stack_base = NULL;
    size_t stack_size = 0;
    int attribute_result = pthread_attr_getstack(&attributes, &stack_base, &stack_size);
    size_t guard_size = 0;
    if (pthread_attr_getguardsize(&attributes, &guard_size)) guard_size = 0;
    pthread_attr_destroy(&attributes);
    uintptr_t low = (uintptr_t)stack_base;
    if (attribute_result || !low || stack_size < 4096 || stack_size > UINTPTR_MAX - low) return -1;
    uintptr_t high = low + stack_size;
    uintptr_t sp = current_sp();
    uintptr_t loader_sp = loader_sp_slot ? *loader_sp_slot : 0;
    struct stack_job job = {work, low, high, thread, logger, -1};
    if (logger) logger(ANDROID_LOG_INFO,
        "Native stack bridge: SP=%p OS=[%p,%p) saved loader=%p",
        (void *)sp, (void *)low, (void *)high, (void *)loader_sp);
    if (sp >= low && sp < high) {
        checked_stack_job(&job);
        return job.status;
    }
    /* The saved loader stack belongs to this same pthread. Its original fibre
     * register frame must remain above SP while the callback grows downward. */
    if (!gateway || !loader_sp_slot || guard_size > stack_size || stack_size - guard_size < 65536 ||
        loader_sp < low + guard_size + 65536 || loader_sp >= high || (loader_sp & 7)) {
        if (logger) logger(ANDROID_LOG_ERROR, "Native stack bridge saved loader SP is invalid for current pthread");
        return -1;
    }
#if defined(__arm__)
    register void *argument __asm__("r0") = &job;
    /* All stack save/restore and game/loader reentry bookkeeping are performed
     * by the original wrapper. This only supplies its R12 target and R0 argument. */
    __asm__ volatile("mov r12, %[target]\n\tblx %[entry]"
        : "+r"(argument)
        : [target] "r"(checked_stack_job), [entry] "r"(gateway)
        : "r1", "r2", "r3", "r12", "lr", "cc", "memory",
          "d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7"
#if defined(__ARM_NEON)
          , "d16", "d17", "d18", "d19", "d20", "d21", "d22", "d23",
          "d24", "d25", "d26", "d27", "d28", "d29", "d30", "d31"
#endif
    );
#else
    if (logger) logger(ANDROID_LOG_ERROR, "Foreign-stack bridge requires ARM32");
#endif
    return job.status;
}
