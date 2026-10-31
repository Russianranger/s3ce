#ifndef S3CE_POINTER_CALLBACKS_H
#define S3CE_POINTER_CALLBACKS_H
#include <stddef.h>
#include <stdint.h>

typedef int32_t (*s3ce_pointer_callback)(void *system_data, void *user_data);
typedef int32_t (*s3ce_pointer_core_register)(int device, int event_count, int event,
        s3ce_pointer_callback callback, void *user_data, uint8_t single);
typedef int32_t (*s3ce_pointer_core_unregister)(int device, int event_count, int event,
        s3ce_pointer_callback callback, void *specific);
typedef s3ce_pointer_callback (*s3ce_pointer_create_proxy)(s3ce_pointer_callback proxy);
typedef int32_t (*s3ce_pointer_invoke)(s3ce_pointer_callback callback,
        void *system_data, void *user_data);
typedef void (*s3ce_pointer_observer)(int event, s3ce_pointer_callback original,
        char *text, size_t capacity);
typedef void (*s3ce_pointer_log)(int priority, const char *format, ...);

/* Bind once before the game starts. create_proxy must request the original
 * generic Int32 stack gateway, never its fast counterpart. invoke must use the
 * original game-callback stack gateway. No JNI methods are called here.
 * Stable slots are never reused; unsupported/capacity failures pass the original
 * game callback unchanged to the original registry. */
void s3ce_pointer_callbacks_bind(s3ce_pointer_core_register register_core,
        s3ce_pointer_core_unregister unregister_core,
        s3ce_pointer_create_proxy create_proxy, s3ce_pointer_invoke invoke,
        s3ce_pointer_observer observer, s3ce_pointer_log logger);
int32_t s3ce_pointer_register_observed(int event, s3ce_pointer_callback callback,
                                     void *user_data);
int32_t s3ce_pointer_unregister_observed(int event, s3ce_pointer_callback callback);
#endif
