/* S3CE compatibility loader, limited to the supplied ARM32 Airplay runtime.
 * The original executable remains a user-supplied asset. No game code is
 * generated or emulated by this shim. Ordinary allocations remain non-executable.
 */
#include <android/asset_manager.h>
#include <android/asset_manager_jni.h>
#include <android/log.h>
#include <android/set_abort_message.h>
#include <dlfcn.h>
#include <elf.h>
#include <errno.h>
#include <jni.h>
#include <limits.h>
#include <pthread.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "graphics_diagnostics.h"
#include "graphics_safety.h"
#include "jni_gl_start.h"
#include "stack_bridge.h"
#include "exception_inspect.h"
#include "code_flush.h"
#include "ui_depth.h"
#include "memory_compat.h"
#include "input_trace.h"
#include "pointer_callbacks.h"
#include "game_pointer_observer.h"
#include "mapped_memory.h"
#include <EGL/egl.h>

static char diagnostic_path[PATH_MAX];
static pthread_mutex_t diagnostic_lock = PTHREAD_MUTEX_INITIALIZER;
static void diagnostic_log(int priority, const char *format, ...) {
    char message[1024];
    va_list arguments;
    va_start(arguments, format);
    vsnprintf(message, sizeof(message), format, arguments);
    va_end(arguments);
    __android_log_write(priority, "S3CECompat", message);
    pthread_mutex_lock(&diagnostic_lock);
    if (diagnostic_path[0]) {
        FILE *output = fopen(diagnostic_path, "a");
        if (output) { fprintf(output, "%s\n", message); fclose(output); }
    }
    pthread_mutex_unlock(&diagnostic_lock);
}
#define LOGE(...) diagnostic_log(ANDROID_LOG_ERROR, __VA_ARGS__)
#define LOGI(...) diagnostic_log(ANDROID_LOG_INFO, __VA_ARGS__)
#define MAX_IMAGE_SIZE (16u * 1024u * 1024u)
#define LEGACY_SIZE 410811u
#define LEGACY_ASSET "compat/libairplay-legacy.so"

/* Compiler-rt implementations preserve the ARM EABI, including multi-register
 * division returns. Taking their addresses pulls the exact builtins into this
 * shared object instead of depending on obsolete Android exports. */
#define EABI_FUNCTIONS(X) \
 X(__aeabi_fadd) X(__aeabi_i2f) X(__aeabi_ui2d) X(__aeabi_dcmplt) \
 X(__aeabi_ddiv) X(__aeabi_dmul) X(__aeabi_lmul) X(__aeabi_d2f) \
 X(__aeabi_fsub) X(__aeabi_dadd) X(__aeabi_idiv) X(__aeabi_dsub) \
 X(__aeabi_f2iz) X(__aeabi_i2d) X(__aeabi_uidiv) X(__aeabi_fmul) \
 X(__aeabi_uidivmod) X(__aeabi_dcmpeq) X(__aeabi_d2iz) X(__aeabi_f2d) \
 X(__aeabi_idivmod) X(__aeabi_ldivmod)
#define DECLARE_EABI(name) extern void name(void);
EABI_FUNCTIONS(DECLARE_EABI)
#undef DECLARE_EABI

static size_t page_size;
static void *legacy_base;
static size_t legacy_mapping_size;
static jint legacy_jni_version;
static int graphics_enabled = 1;
static JavaVM *runtime_vm;
static void (*original_gl_start)(void);
static void **original_android_state;
static uint32_t *original_gl_version;
static const uintptr_t *original_loader_sp_slot;
static void (*original_stack_gateway)(void);
static int (*original_platform_cache_flush)(void *, uint32_t);
static const uint8_t *original_stack_switch_flag;
static const uintptr_t *original_dynamic_space_slot;
static s3ce_pointer_callback (*original_dynamic_callback)(s3ce_pointer_callback, unsigned, unsigned);
static uintptr_t original_pointer_proxy_gateway;
static int32_t (*original_callback_gateway)(s3ce_pointer_callback, void *, void *,
    uintptr_t, uintptr_t, uintptr_t, uintptr_t, uintptr_t);
static unsigned expanded_flush_logs;
static pthread_mutex_t load_lock = PTHREAD_MUTEX_INITIALIZER;

struct code_allocation {
    struct code_allocation *next;
    void *address;
    size_t length;
    int ui_depth_status;
};
static struct code_allocation *code_allocations;
static pthread_mutex_t code_lock = PTHREAD_MUTEX_INITIALIZER;

static size_t page_up(size_t n) { return (n + page_size - 1) & ~(page_size - 1); }

/* Airplay explicitly has separate s3eMallocOSCode/s3eFreeOSCode entry points.
 * Only these are redirected. Its S3E image combines mutable data and ARM code,
 * so that allocation must stay writable while executing the legacy program. */
static void *allocate_game_code(uint32_t requested) {
    if (!requested || requested > MAX_IMAGE_SIZE) return NULL;
    size_t length = page_up(requested);
    void *result = mmap(NULL, length, PROT_READ | PROT_WRITE | PROT_EXEC,
                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (result == MAP_FAILED) {
        LOGE("S3E executable allocation failed (%u bytes): %s", requested, strerror(errno));
        return NULL;
    }
    struct code_allocation *entry = malloc(sizeof(*entry));
    if (!entry) { munmap(result, length); return NULL; }
    entry->address = result;
    entry->length = length;
    entry->ui_depth_status = 0;
    pthread_mutex_lock(&code_lock);
    entry->next = code_allocations;
    code_allocations = entry;
    pthread_mutex_unlock(&code_lock);
    LOGI("Allocated explicit S3E code region: %u bytes at %p; StackSwitch=%d", requested, result,
         original_stack_switch_flag ? *original_stack_switch_flag : -1);
    return result;
}

static void free_game_code(void *address) {
    if (!address) return;
    pthread_mutex_lock(&code_lock);
    struct code_allocation **entry = &code_allocations;
    while (*entry && (*entry)->address != address) entry = &(*entry)->next;
    struct code_allocation *found = *entry;
    if (found) *entry = found->next;
    pthread_mutex_unlock(&code_lock);
    if (!found) { LOGE("Unknown S3E code free rejected: %p", address); return; }
    munmap(found->address, found->length);
    free(found);
}

static int flush_legacy_code(void *start, uint32_t length) {
    pthread_mutex_lock(&code_lock);
    struct code_allocation *entry = code_allocations;
    uintptr_t address = (uintptr_t)start;
    while (entry) {
        uintptr_t base = (uintptr_t)entry->address;
        if (address >= base && address - base < entry->length &&
            length <= entry->length - (address - base)) break;
        entry = entry->next;
    }
    if (entry && !entry->ui_depth_status) {
        int patched = s3ce_patch_ui_depth(entry->address, entry->length, start, length);
        if (patched) {
            entry->ui_depth_status = patched;
            if (patched > 0)
                LOGI("UI projection depth fixed: %p+0x135d80 uses XY scale and Z=1 (%s)",
                     entry->address, patched == 1 ? "patched" : "already patched");
            else
                LOGE("UI depth scale patch refused: unexpected projection-wrapper fingerprint at %p", entry->address);
        }
    }
    int result = s3ce_flush_code_span(start, length, entry ? entry->address : NULL,
        entry ? entry->length : 0, original_platform_cache_flush);
    if (entry && expanded_flush_logs++ < 8)
        LOGI("S3E cache flush expanded: request=%p+%u allocation=%p+%zu result=%d",
             start, length, entry->address, entry->length, result);
    pthread_mutex_unlock(&code_lock);
    return result;
}

static void read_legacy_memory_info(int *total, int *free_bytes) {
    s3ce_get_memory_info(total, free_bytes, diagnostic_log);
}

static s3ce_pointer_callback create_pointer_proxy(s3ce_pointer_callback proxy) {
    /* Generic Int32 is required: the fast gateway does not save current game
     * frames before a native observer reenters an original game callback. */
    s3ce_pointer_callback result = original_dynamic_callback(proxy, 4, 0);
    if (!original_stack_switch_flag || !*original_stack_switch_flag)
        return result == proxy ? result : NULL;
    uintptr_t address = (uintptr_t)result;
    uintptr_t arena = original_dynamic_space_slot ? *original_dynamic_space_slot : 0;
    if (!address || (address & 3) || !arena || address < arena || address - arena > 1024 - 16)
        return NULL;
    pthread_mutex_lock(&code_lock);
    struct code_allocation *entry = code_allocations;
    while (entry) {
        uintptr_t start = (uintptr_t)entry->address;
        if (address >= start && address - start <= entry->length &&
            16 <= entry->length - (address - start)) break;
        entry = entry->next;
    }
    uint32_t words[4] = {0};
    if (entry) memcpy(words, (const void *)address, sizeof(words));
    int valid = entry != NULL;
    pthread_mutex_unlock(&code_lock);
    if (!valid || words[0] != 0xe59fc000 || words[1] != 0xe59ff000 ||
        words[2] != (uint32_t)(uintptr_t)proxy ||
        words[3] != (uint32_t)original_pointer_proxy_gateway) return NULL;
    return result;
}

static int32_t invoke_pointer_callback(s3ce_pointer_callback callback, void *system, void *user) {
    return original_callback_gateway(callback, system, user, 0, 0, 0, 0, 0);
}

static void observe_pointer_game(int event, s3ce_pointer_callback callback,
                                 char *text, size_t capacity) {
    (void)event;
    uintptr_t address = (uintptr_t)callback;
    pthread_mutex_lock(&code_lock);
    struct code_allocation *entry = code_allocations;
    while (entry) {
        uintptr_t start = (uintptr_t)entry->address;
        if (address >= start && address - start < entry->length) break;
        entry = entry->next;
    }
    if (!entry) {
        snprintf(text, capacity, "Game input snapshot unavailable: callback outside tracked code");
    } else {
        /* Original pointer adapters only append to AppEngine's event arrays;
         * they cannot destroy AppEngine/Scene. Observe synchronously on that
         * same engine thread, with a complete readable-range check per copy.
         * The code lock also prevents the tracked code mapping being freed. */
        struct s3ce_readable_memory readable;
        if (!s3ce_load_readable_memory(&readable))
            snprintf(text, capacity, "Game input snapshot unavailable: readable maps");
        else
            s3ce_observe_game_pointer((uintptr_t)entry->address, address,
                s3ce_read_mapped_memory, &readable, text, capacity);
    }
    pthread_mutex_unlock(&code_lock);
}

static int legacy_exception_status(void) {
    JNIEnv *env = NULL;
    if (!runtime_vm || (*runtime_vm)->GetEnv(runtime_vm, (void **)&env, JNI_VERSION_1_6) != JNI_OK)
        return -1;
    return (*env)->ExceptionCheck(env) ? 1 : 0;
}

/* This adapter is entered from a legacy capability query on the engine thread.
 * Reuse Airplay's existing mutex release/UI-view creation/relock protocol. */
static void legacy_initialize_window_context_on_thread_stack(void) {
    JNIEnv *env = NULL;
    int attached = runtime_vm && (*runtime_vm)->GetEnv(runtime_vm, (void **)&env, JNI_VERSION_1_6) == JNI_OK;
    int env_matches = attached && original_android_state && original_android_state[0] == (void *)env;
    int thread_present = original_android_state && original_android_state[0x08 / 4] != NULL;
    int method_present = original_android_state && original_android_state[0x14 / 4] != NULL;
    int lock_present = original_android_state && original_android_state[0x10c / 4] != NULL;
    LOGI("Original GL bootstrap state: engine JNI=%d thread=%d glInit=%d lock=%d exception=%d",
         env_matches, thread_present, method_present, lock_present, legacy_exception_status());
    if (!env_matches || !thread_present || !lock_present || !original_gl_start || !original_gl_version ||
        (*env)->ExceptionCheck(env)) {
        LOGE("Original GL bootstrap prerequisites failed");
        if (attached && env && (*env)->ExceptionCheck(env))
            s3ce_record_pending_gl_exception(env, diagnostic_log);
        return;
    }
    jobject retained_receiver = (*env)->NewLocalRef(env, (jobject)original_android_state[0x08 / 4]);
    if (!retained_receiver || (*env)->ExceptionCheck(env)) {
        s3ce_record_pending_gl_exception(env, diagnostic_log);
        return;
    }
    jint version = *original_gl_version > 0x1ff ? 2 : 1;
    jmethodID fresh_private = NULL;
    int typed_result = s3ce_call_java_gl_init(env, retained_receiver,
        (jmethodID)original_android_state[0x14 / 4], version, &fresh_private, diagnostic_log);
    EGLContext current = eglGetCurrentContext();
    int pending = legacy_exception_status();
    LOGI("Typed GL bootstrap validation: result=%d current=%p JNI exception=%d",
         typed_result, (void *)current, pending);
    if (typed_result || pending > 0 || current == EGL_NO_CONTEXT) {
        (*env)->DeleteLocalRef(env, retained_receiver);
        return;
    }
    /* setViewNative can replace its global handle while the bridge creates the
     * GL view. The retained local stays valid; reread and compare the new handle. */
    jboolean same_receiver = (*env)->IsSameObject(env, retained_receiver,
        (jobject)original_android_state[0x08 / 4]);
    if ((*env)->ExceptionCheck(env)) {
        s3ce_record_pending_gl_exception(env, diagnostic_log);
        (*env)->DeleteLocalRef(env, retained_receiver);
        return;
    }
    (*env)->DeleteLocalRef(env, retained_receiver);
    if (!same_receiver || !fresh_private) {
        LOGE("GL bootstrap receiver changed; refusing to refresh a different receiver's JNI cache");
        android_set_abort_message("S3CE GL bootstrap receiver changed during window initialization");
        abort();
    }
    original_android_state[0x14 / 4] = (void *)fresh_private;
    LOGI("Original GL private method cache refreshed for the current receiver");
    /* The typed bridge established the real context and m_UseGL. Reuse the
     * original callback's GL tracking/version bookkeeping afterward; its Java
     * initializer now sees m_UseGL and skips duplicate window work. */
    LOGI("Original GL bookkeeping begin after typed initialization");
    original_gl_start();
    LOGI("Original GL bookkeeping returned");
}

static void legacy_initialize_window_context(void) {
    if (s3ce_call_on_thread_stack(legacy_initialize_window_context_on_thread_stack,
            original_loader_sp_slot, original_stack_gateway, diagnostic_log)) {
        LOGE("GL startup refused an invalid current-thread/loader-stack transition");
        android_set_abort_message("S3CE GL startup cannot enter the current pthread's native stack");
        abort();
    }
}

static void *legacy_dlsym(void *handle, const char *name) {
    void *actual = dlsym(handle, name);
    return s3ce_graphics_symbol(handle, name, actual, diagnostic_log);
}

static int legacy_srget(FILE *stream) { return getc(stream); }
static int legacy_atexit(void (*handler)(void)) { return atexit(handler); }
static void *legacy_new(size_t size) { return malloc(size ? size : 1); }
static void legacy_delete(void *address) { free(address); }

static void *resolve_import(const char *name, void **handles, size_t handle_count) {
#define MATCH_EABI(symbol) if (!strcmp(name, #symbol)) return (void *)(uintptr_t)&symbol;
    EABI_FUNCTIONS(MATCH_EABI)
#undef MATCH_EABI
    if (graphics_enabled && !strcmp(name, "dlsym")) return (void *)(uintptr_t)&legacy_dlsym;
    if (!strcmp(name, "atexit")) return (void *)(uintptr_t)&legacy_atexit;
    if (!strcmp(name, "__srget")) return (void *)(uintptr_t)&legacy_srget;
    if (!strcmp(name, "_Znaj") || !strcmp(name, "_Znwj"))
        return (void *)(uintptr_t)&legacy_new;
    if (!strcmp(name, "_ZdlPv") || !strcmp(name, "_ZdaPv"))
        return (void *)(uintptr_t)&legacy_delete;
    void *symbol = dlsym(RTLD_DEFAULT, name);
    for (size_t i = 0; !symbol && i < handle_count; ++i)
        symbol = dlsym(handles[i], name);
    return symbol;
}

static int span_ok(size_t total, uint32_t offset, size_t length) {
    return offset <= total && length <= total - offset;
}

struct image {
    uint8_t *base;
    size_t size;
    Elf32_Sym *symbols;
    uint32_t symbol_count;
    const char *strings;
    uint32_t strings_size;
    void *handles[8];
    size_t handle_count;
};

static void *image_pointer(struct image *image, uint32_t offset, size_t length) {
    return span_ok(image->size, offset, length) ? image->base + offset : NULL;
}

static const char *symbol_name(struct image *image, uint32_t offset) {
    if (offset >= image->strings_size) return NULL;
    const char *name = image->strings + offset;
    return memchr(name, 0, image->strings_size - offset) ? name : NULL;
}

static int relocate(struct image *image, uint32_t offset, uint32_t size) {
    if (size % sizeof(Elf32_Rel)) return -1;
    Elf32_Rel *relocations = image_pointer(image, offset, size);
    if (!relocations && size) return -1;
    for (size_t i = 0; i < size / sizeof(Elf32_Rel); ++i) {
        Elf32_Rel *rel = &relocations[i];
        if (rel->r_offset % sizeof(uint32_t)) return -1;
        uint32_t *target = image_pointer(image, rel->r_offset, sizeof(*target));
        uint32_t type = ELF32_R_TYPE(rel->r_info);
        uint32_t sym = ELF32_R_SYM(rel->r_info);
        if (!target) return -1;
        if (type == R_ARM_NONE) continue;
        if (type == R_ARM_RELATIVE) {
            if (sym) return -1;
            *target += (uint32_t)(uintptr_t)image->base;
            continue;
        }
        if (sym >= image->symbol_count) return -1;
        Elf32_Sym *symbol = &image->symbols[sym];
        const char *name = symbol_name(image, symbol->st_name);
        if (!name) return -1;
        uintptr_t address;
        if (symbol->st_shndx == SHN_UNDEF) {
            address = (uintptr_t)resolve_import(name, image->handles, image->handle_count);
            if (!address && ELF32_ST_BIND(symbol->st_info) != STB_WEAK) {
                LOGE("Unresolved legacy import: %s", name);
                return -1;
            }
        } else if (symbol->st_shndx == SHN_ABS) {
            address = symbol->st_value;
        } else {
            if (symbol->st_value >= image->size) return -1;
            address = (uintptr_t)image->base + symbol->st_value;
        }
        if (type == R_ARM_ABS32) *target += (uint32_t)address;
        else if (type == R_ARM_GLOB_DAT || type == R_ARM_JUMP_SLOT) *target = (uint32_t)address;
        else { LOGE("Unsupported ARM relocation: %u", type); return -1; }
    }
    return 0;
}

static int patch_thumb_function(struct image *image, uint32_t address,
                                const uint8_t expected[8], void *replacement) {
    uint8_t *target = image_pointer(image, address, 8);
    if (!target || memcmp(target, expected, 8)) {
        LOGE("Legacy allocator fingerprint mismatch at %x", address);
        return -1;
    }
    /* Thumb-2 LDR.W PC,[PC,#0], followed by interworking destination. */
    static const uint8_t jump[4] = { 0xdf, 0xf8, 0x00, 0xf0 };
    uint32_t destination = (uint32_t)(uintptr_t)replacement;
    memcpy(target, jump, sizeof(jump));
    memcpy(target + 4, &destination, sizeof(destination));
    return 0;
}

static jint load_legacy(JNIEnv *env, JavaVM *vm, jobject asset_manager) {
    AAssetManager *manager = AAssetManager_fromJava(env, asset_manager);
    if (!manager) { LOGE("No Android asset manager"); return JNI_ERR; }
    AAsset *asset = AAssetManager_open(manager, LEGACY_ASSET, AASSET_MODE_BUFFER);
    if (!asset) { LOGE("Missing %s", LEGACY_ASSET); return JNI_ERR; }
    size_t input_size = (size_t)AAsset_getLength(asset);
    const uint8_t *input = AAsset_getBuffer(asset);
    struct image image = {0};
    const Elf32_Ehdr *header = (const Elf32_Ehdr *)input;
    const Elf32_Phdr *programs = NULL;
    Elf32_Dyn *dynamic = NULL;
    size_t dynamic_count = 0;
    uint32_t rel = 0, rel_size = 0, jmprel = 0, jmprel_size = 0;
    uint32_t strings = 0, symbols = 0, hash = 0;
    jint result = JNI_ERR;
    const char *phase = "validate ELF";
    if (!input || input_size != LEGACY_SIZE || input_size < sizeof(*header) ||
        memcmp(header->e_ident, ELFMAG, SELFMAG) ||
        header->e_ident[EI_CLASS] != ELFCLASS32 || header->e_ident[EI_DATA] != ELFDATA2LSB ||
        header->e_type != ET_DYN || header->e_machine != EM_ARM ||
        header->e_phentsize != sizeof(Elf32_Phdr) || !header->e_phnum || header->e_phnum > 16 ||
        !span_ok(input_size, header->e_phoff, header->e_phnum * sizeof(Elf32_Phdr))) goto done;
    programs = (const Elf32_Phdr *)(input + header->e_phoff);
    for (size_t i = 0; i < header->e_phnum; ++i) {
        const Elf32_Phdr *p = &programs[i];
        if (p->p_type != PT_LOAD) continue;
        if (p->p_filesz > p->p_memsz || !span_ok(input_size, p->p_offset, p->p_filesz) ||
            p->p_vaddr > MAX_IMAGE_SIZE || p->p_memsz > MAX_IMAGE_SIZE - p->p_vaddr) goto done;
        size_t end = p->p_vaddr + p->p_memsz;
        if (end > image.size) image.size = end;
    }
    phase = "map load segments";
    if (!image.size || image.size > MAX_IMAGE_SIZE) goto done;
    image.size = page_up(image.size);
    image.base = mmap(NULL, image.size, PROT_READ | PROT_WRITE,
                       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (image.base == MAP_FAILED) { image.base = NULL; goto done; }
    for (size_t i = 0; i < header->e_phnum; ++i) {
        const Elf32_Phdr *p = &programs[i];
        if (p->p_type == PT_LOAD) memcpy(image.base + p->p_vaddr, input + p->p_offset, p->p_filesz);
        if (p->p_type == PT_DYNAMIC) {
            if (dynamic || p->p_memsz % sizeof(Elf32_Dyn)) goto done;
            dynamic = image_pointer(&image, p->p_vaddr, p->p_memsz);
            dynamic_count = p->p_memsz / sizeof(Elf32_Dyn);
        }
    }
    phase = "parse dynamic table";
    if (!dynamic || dynamic_count > 128) goto done;
    int terminated = 0;
    for (size_t i = 0; i < dynamic_count; ++i) {
        Elf32_Dyn *entry = &dynamic[i];
        if (entry->d_tag == DT_NULL) { terminated = 1; break; }
        switch (entry->d_tag) {
            case DT_STRTAB: strings = entry->d_un.d_ptr; break;
            case DT_STRSZ: image.strings_size = entry->d_un.d_val; break;
            case DT_SYMTAB: symbols = entry->d_un.d_ptr; break;
            case DT_SYMENT: if (entry->d_un.d_val != sizeof(Elf32_Sym)) goto done; break;
            case DT_HASH: hash = entry->d_un.d_ptr; break;
            case DT_REL: rel = entry->d_un.d_ptr; break;
            case DT_RELSZ: rel_size = entry->d_un.d_val; break;
            case DT_RELENT: if (entry->d_un.d_val != sizeof(Elf32_Rel)) goto done; break;
            case DT_JMPREL: jmprel = entry->d_un.d_ptr; break;
            case DT_PLTRELSZ: jmprel_size = entry->d_un.d_val; break;
            case DT_PLTREL: if (entry->d_un.d_val != DT_REL) goto done; break;
            case DT_INIT: case DT_INIT_ARRAY: case DT_PREINIT_ARRAY: case DT_RELA: goto done;
        }
    }
    uint32_t *hash_header = image_pointer(&image, hash, 8);
    if (!terminated || !hash_header || !hash || !strings || !symbols ||
        hash_header[1] > 65536 || !hash_header[1]) goto done;
    image.symbol_count = hash_header[1];
    image.symbols = image_pointer(&image, symbols, image.symbol_count * sizeof(Elf32_Sym));
    image.strings = image_pointer(&image, strings, image.strings_size);
    if (!image.symbols || !image.strings) goto done;
    phase = "resolve dependencies";
    for (size_t i = 0; i < dynamic_count && dynamic[i].d_tag != DT_NULL; ++i) {
        if (dynamic[i].d_tag != DT_NEEDED) continue;
        const char *name = symbol_name(&image, dynamic[i].d_un.d_val);
        if (!name || image.handle_count >= 8) goto done;
        if (strcmp(name, "libc.so") && strcmp(name, "libm.so") && strcmp(name, "liblog.so") &&
            strcmp(name, "libstdc++.so") && strcmp(name, "libz.so") && strcmp(name, "libdl.so")) goto done;
        void *handle = dlopen(name, RTLD_NOW | RTLD_LOCAL);
        if (!handle) { LOGE("Cannot open %s: %s", name, dlerror()); goto done; }
        image.handles[image.handle_count++] = handle;
    }
    phase = "apply relocations";
    if (relocate(&image, rel, rel_size) || relocate(&image, jmprel, jmprel_size)) goto done;
    phase = "patch dedicated S3E allocator";
    static const uint8_t malloc_code[8] = {0x00,0xb5,0x81,0xb0,0x00,0xf0,0x18,0xf8};
    static const uint8_t free_code[8] = {0x00,0xb5,0x81,0xb0,0x00,0xf0,0x96,0xfe};
    static const uint8_t get_string_code[8] = {0xf0,0xb5,0x19,0x4e,0x81,0xb0,0x33,0x6a};
    void **get_string_slot = image_pointer(&image, 0x55a64, sizeof(void *));
    if (!get_string_slot) goto done;
    static const uint8_t gl_start_code[8] = {0x10,0xb5,0x10,0x4c,0x10,0x4b,0x22,0x68};
    uint8_t *gl_start = image_pointer(&image, 0x210a4, sizeof(gl_start_code));
    if (!gl_start || memcmp(gl_start, gl_start_code, sizeof(gl_start_code))) goto done;
    uint32_t *android_literal = image_pointer(&image, 0x210f0, sizeof(uint32_t));
    original_android_state = image_pointer(&image, 0x53af0, 276);
    if (!android_literal || *android_literal != (uint32_t)(uintptr_t)(image.base + 0x53af0) ||
        !original_android_state) goto done;
    original_gl_version = image_pointer(&image, 0x55a04, sizeof(uint32_t));
    if (!original_gl_version) goto done;
    static const uint8_t stack_gateway_code[12] = {
        0x00,0x40,0x2d,0xe9,0x97,0xff,0xff,0xeb,0x00,0x40,0xbd,0xe8};
    uint8_t *stack_gateway = image_pointer(&image, 0x3c7f0, sizeof(stack_gateway_code));
    uint32_t *loader_literal = image_pointer(&image, 0x3c750, sizeof(uint32_t));
    original_loader_sp_slot = image_pointer(&image, 0x56758, sizeof(uintptr_t));
    if (!stack_gateway || memcmp(stack_gateway, stack_gateway_code, sizeof(stack_gateway_code)) ||
        !loader_literal || *loader_literal != (uint32_t)(uintptr_t)(image.base + 0x56758) ||
        !original_loader_sp_slot) goto done;
    static const uint8_t platform_flush_code[8] = {0xf0,0xb5,0x05,0x1c,0x0e,0x1c,0x03,0x0b};
    uint8_t *platform_flush = image_pointer(&image, 0x41020, sizeof(platform_flush_code));
    if (!platform_flush || memcmp(platform_flush, platform_flush_code, sizeof(platform_flush_code))) goto done;
    original_platform_cache_flush = (int (*)(void *, uint32_t))(uintptr_t)(image.base + 0x41021);
    original_stack_switch_flag = image_pointer(&image, 0x54b68 + 0x18, 1);
    original_dynamic_space_slot = image_pointer(&image, 0x54b68 + 0x10, sizeof(uintptr_t));
    static const uint32_t callback_addresses[4] = {0x26edc,0x27524,0x3c558,0x3c9a0};
    static const uint8_t callback_guards[4][8] = {
        {0x30,0xb5,0x85,0xb0,0x08,0xac,0x20,0xcc},
        {0xf0,0xb5,0x57,0x46,0x4e,0x46,0x45,0x46},
        {0xf0,0x4f,0x2d,0xe9,0x00,0x50,0xa0,0xe1},
        {0xf0,0xb5,0x81,0xb0,0x0e,0x1c,0x17,0x1c}};
    if (!original_stack_switch_flag || !original_dynamic_space_slot) goto done;
    uint32_t *proxy_gateway_literal = image_pointer(&image, 0x3ca94, sizeof(uint32_t));
    original_pointer_proxy_gateway = (uintptr_t)(image.base + 0x3c808);
    if (!proxy_gateway_literal || *proxy_gateway_literal != original_pointer_proxy_gateway) goto done;
    for (unsigned i = 0; i < 4; ++i) {
        const uint8_t *code = image_pointer(&image, callback_addresses[i], 8);
        if (!code || memcmp(code, callback_guards[i], 8)) goto done;
    }
    original_dynamic_callback = (s3ce_pointer_callback (*)(s3ce_pointer_callback, unsigned, unsigned))
        (uintptr_t)(image.base + 0x3c9a1);
    original_callback_gateway = (int32_t (*)(s3ce_pointer_callback, void *, void *,
        uintptr_t, uintptr_t, uintptr_t, uintptr_t, uintptr_t))(uintptr_t)(image.base + 0x3c558);
    s3ce_pointer_callbacks_bind(
        (s3ce_pointer_core_register)(uintptr_t)(image.base + 0x26edd),
        (s3ce_pointer_core_unregister)(uintptr_t)(image.base + 0x27525),
        create_pointer_proxy, invoke_pointer_callback, observe_pointer_game, diagnostic_log);
    original_stack_gateway = (void (*)(void))(uintptr_t)(image.base + 0x3c7f0);
    original_gl_start = (void (*)(void))(uintptr_t)(image.base + 0x210a5);
    s3ce_gl_safety_bind(get_string_slot, diagnostic_log,
        legacy_initialize_window_context, legacy_exception_status);
    static const uint8_t memory_info_code[8] = {0xf0,0xb5,0x47,0x46,0x80,0xb4,0x1b,0x4c};
    static const uint8_t cache_flush_code[8] = {0x2a,0xf0,0x2a,0xbb,0x42,0x18,0x03,0x4c};
    static const uint8_t pointer_register_code[8] = {0x10,0xb5,0x82,0xb0,0x04,0x1c,0x00,0x92};
    static const uint8_t pointer_unregister_code[8] = {0x00,0xb5,0x83,0xb0,0x0b,0x1c,0x00,0x21};
    if (patch_thumb_function(&image, 0x3752c, pointer_register_code, (void *)(uintptr_t)&s3ce_pointer_register_observed) ||
        patch_thumb_function(&image, 0x3766c, pointer_unregister_code, (void *)(uintptr_t)&s3ce_pointer_unregister_observed) ||
        patch_thumb_function(&image, 0x223b8, memory_info_code, (void *)(uintptr_t)&read_legacy_memory_info) ||
        patch_thumb_function(&image, 0x169c8, cache_flush_code, (void *)(uintptr_t)&flush_legacy_code) ||
        patch_thumb_function(&image, 0x37148, malloc_code, (void *)(uintptr_t)&allocate_game_code) ||
        patch_thumb_function(&image, 0x36434, free_code, (void *)(uintptr_t)&free_game_code) ||
        patch_thumb_function(&image, 0x3397c, get_string_code, (void *)(uintptr_t)&s3ce_safe_gl_get_string)) goto done;
    phase = "bind bounded native input diagnostics";
    uint32_t *motion_registration = image_pointer(&image, 0x457d8, 12);
    const char *motion_name = image_pointer(&image, 0x46140, sizeof("onMotionEvent"));
    const char *motion_signature = image_pointer(&image, 0x46150, sizeof("(IIII)V"));
    const uint8_t *pointer_state = image_pointer(&image, 0x55d80, 48);
    static const uint8_t motion_code[8] = {0x00,0xb5,0x10,0x1c,0x19,0x1c,0x86,0x22};
    const uint8_t *motion_entry = image_pointer(&image, 0x2148c, sizeof(motion_code));
    if (!motion_registration || !motion_name || !motion_signature || !pointer_state ||
        !motion_entry || memcmp(motion_entry, motion_code, sizeof(motion_code)) ||
        motion_registration[0] != (uint32_t)(uintptr_t)(image.base + 0x46140) ||
        motion_registration[1] != (uint32_t)(uintptr_t)(image.base + 0x46150) ||
        motion_registration[2] != (uint32_t)(uintptr_t)(image.base + 0x2148d) ||
        memcmp(motion_name, "onMotionEvent", sizeof("onMotionEvent")) ||
        memcmp(motion_signature, "(IIII)V", sizeof("(IIII)V"))) goto done;
    s3ce_input_motion traced_motion = s3ce_input_trace_prepare(
        (s3ce_input_motion)(uintptr_t)motion_registration[2], pointer_state, diagnostic_log);
    if (!traced_motion) goto done;
    motion_registration[2] = (uint32_t)(uintptr_t)traced_motion;
    phase = "protect legacy segments";
    if (mprotect(image.base, image.size, PROT_NONE)) goto done;
    for (size_t i = 0; i < header->e_phnum; ++i) {
        const Elf32_Phdr *p = &programs[i];
        if (p->p_type != PT_LOAD) continue;
        int protection = ((p->p_flags & PF_R) ? PROT_READ : 0) |
                         ((p->p_flags & PF_W) ? PROT_WRITE : 0) |
                         ((p->p_flags & PF_X) ? PROT_EXEC : 0);
        uintptr_t start = p->p_vaddr & ~(page_size - 1);
        size_t length = page_up(p->p_vaddr + p->p_memsz) - start;
        if ((protection & (PROT_WRITE | PROT_EXEC)) == (PROT_WRITE | PROT_EXEC) ||
            mprotect(image.base + start, length, protection)) goto done;
        if (protection & PROT_EXEC)
            __builtin___clear_cache((char *)image.base + start, (char *)image.base + start + length);
    }
    phase = "register legacy JNI methods";
    uintptr_t onload = 0;
    for (uint32_t i = 0; i < image.symbol_count; ++i) {
        const char *name = symbol_name(&image, image.symbols[i].st_name);
        if (name && !strcmp(name, "JNI_OnLoad") && image.symbols[i].st_shndx != SHN_UNDEF &&
            image.symbols[i].st_value < image.size)
            onload = (uintptr_t)image.base + image.symbols[i].st_value;
    }
    if (!onload) goto done;
    result = ((jint (*)(JavaVM *, void *))onload)(vm, NULL);
    if ((*env)->ExceptionCheck(env) ||
        (result != JNI_VERSION_1_2 && result != JNI_VERSION_1_4 && result != JNI_VERSION_1_6)) {
        LOGE("Original JNI_OnLoad failed: %x", result);
        result = JNI_ERR;
        goto done;
    }
    legacy_base = image.base;
    legacy_mapping_size = image.size;
    LOGI("Loaded ARM32 Airplay runtime at %p, %zu bytes; JNI version %x", image.base, image.size, result);

done:
    AAsset_close(asset);
    if (result == JNI_ERR) {
        LOGE("Legacy load failed during %s; errno=%d (%s)", phase, errno, strerror(errno));
        s3ce_gl_safety_bind(NULL, NULL, NULL, NULL);
        original_gl_start = NULL;
        original_android_state = NULL;
        original_gl_version = NULL;
        original_loader_sp_slot = NULL;
        original_stack_gateway = NULL;
        original_platform_cache_flush = NULL;
        original_stack_switch_flag = NULL;
        if (image.base) munmap(image.base, image.size);
        for (size_t i = 0; i < image.handle_count; ++i) dlclose(image.handles[i]);
    }
    return result;
}

/* Configure only before the legacy runtime exists. Original-renderer mode
 * bypasses all GL interception and follows the 0.1.0 symbol-resolution path. */
JNIEXPORT jboolean JNICALL Java_com_ideaworks3d_thesims3_GameBootActivity_nativeConfigureGraphics(
        JNIEnv *env, jclass klass, jboolean enabled) {
    (void)env;
    (void)klass;
    int requested = enabled == JNI_TRUE;
    pthread_mutex_lock(&load_lock);
    if (legacy_base && graphics_enabled != requested) {
        pthread_mutex_unlock(&load_lock);
        return JNI_FALSE;
    }
    graphics_enabled = requested;
    pthread_mutex_unlock(&load_lock);
    return JNI_TRUE;
}

/* Explicit bootstrap keeps all Android framework access in public Java APIs.
 * Call after System.loadLibrary("airplay") and before the original Activity.
 * Loading the original Java classes during RegisterNatives then uses the same
 * application ClassLoader as this entry point. */
JNIEXPORT jint JNICALL Java_com_ideaworks3d_thesims3_GameBootActivity_nativeBootstrap(
        JNIEnv *env, jclass klass, jobject assets, jstring files_directory) {
    (void)klass;
    JavaVM *vm = NULL;
    if (!assets || !files_directory || (*env)->GetJavaVM(env, &vm) != JNI_OK) return JNI_ERR;
    pthread_mutex_lock(&load_lock);
    if (!legacy_base) {
        const char *path = (*env)->GetStringUTFChars(env, files_directory, NULL);
        if (!path) { pthread_mutex_unlock(&load_lock); return JNI_ERR; }
        int written = snprintf(diagnostic_path, sizeof(diagnostic_path), "%s/compat-native.log", path);
        (*env)->ReleaseStringUTFChars(env, files_directory, path);
        if (written < 0 || (size_t)written >= sizeof(diagnostic_path)) {
            diagnostic_path[0] = 0;
            pthread_mutex_unlock(&load_lock);
            return JNI_ERR;
        }
        FILE *fresh_log = fopen(diagnostic_path, "w");
        if (fresh_log) fclose(fresh_log);
        LOGI("S3CE ARM32 compatibility loader starting; page size %zu; graphics mode=%s",
             page_size, graphics_enabled ? "PVRTC compatibility" : "original (no GL hooks)");
        /* Native classification is diagnostic-only; a partial cache is usable. */
        s3ce_exception_inspect_cache(env, diagnostic_log);
        if (s3ce_prepare_java_gl_diagnostics(env, diagnostic_log)) {
            LOGE("Could not prepare typed GL diagnostic Java helper");
            legacy_jni_version = JNI_ERR;
        } else {
            legacy_jni_version = load_legacy(env, vm, assets);
        }
    }
    jint result = legacy_jni_version;
    pthread_mutex_unlock(&load_lock);
    return result;
}

JNIEXPORT jint JNI_OnLoad(JavaVM *vm, void *reserved) {
    runtime_vm = vm;
    (void)reserved;
    page_size = (size_t)sysconf(_SC_PAGESIZE);
    if (page_size != 4096) { LOGE("This ARM32 runtime requires 4 KiB pages"); return JNI_ERR; }
    return JNI_VERSION_1_6;
}
