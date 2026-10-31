#!/usr/bin/env bash
set -euo pipefail
native_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
test_dir="$(mktemp -d)"
trap 'python3 -c '\''import shutil,sys; shutil.rmtree(sys.argv[1])'\'' "$test_dir"' EXIT
flags=(-O2 -Wall -Wextra -Werror)
if [[ "${S3CE_SANITIZERS:-0}" == 1 ]]; then
    flags+=(-fsanitize=address,undefined -fno-omit-frame-pointer)
    # LeakSanitizer cannot inspect this managed runtime's process sandbox.
    export ASAN_OPTIONS="${ASAN_OPTIONS:-detect_leaks=0}"
fi
cc -std=gnu11 "${flags[@]}" -I "$native_dir/tests/include" \
    -c "$native_dir/tests/graphics_diagnostics_test.c" -o "$test_dir/graphics.o"
c++ -std=c++14 "${flags[@]}" "$test_dir/graphics.o" \
    "$native_dir/pvrtc/PVRTDecompress.cpp" "$native_dir/pvrtc/pvrtc_bridge.cpp" \
    -ldl -o "$test_dir/graphics_test"
"$test_dir/graphics_test"
cc -std=gnu11 "${flags[@]}" -I "$native_dir/tests/include" \
    "$native_dir/tests/graphics_safety_test.c" -o "$test_dir/safety_test"
"$test_dir/safety_test"
cc -std=gnu11 "${flags[@]}" "$native_dir/tests/code_flush_test.c" -o "$test_dir/flush_test"
"$test_dir/flush_test"
cc -std=gnu11 "${flags[@]}" -I "$native_dir/tests/include" \
    "$native_dir/tests/memory_compat_test.c" -o "$test_dir/memory_test"
"$test_dir/memory_test"
cc -std=gnu11 "${flags[@]}" "$native_dir/tests/pointer_callbacks_test.c" \
    "$native_dir/pointer_callbacks.c" -pthread -o "$test_dir/pointer_test"
"$test_dir/pointer_test"
cc -std=gnu11 "${flags[@]}" "$native_dir/tests/game_pointer_observer_test.c" \
    "$native_dir/game_pointer_observer.c" -o "$test_dir/observer_test"
"$test_dir/observer_test"
cc -std=gnu11 "${flags[@]}" "$native_dir/tests/mapped_memory_test.c" \
    "$native_dir/mapped_memory.c" -o "$test_dir/mapped_test"
"$test_dir/mapped_test"
c++ -std=c++14 "${flags[@]}" "$native_dir/pvrtc/test_bridge.cpp" \
    "$native_dir/pvrtc/PVRTDecompress.cpp" "$native_dir/pvrtc/pvrtc_bridge.cpp" \
    -o "$test_dir/decoder_test"
"$test_dir/decoder_test"

if [[ -n "${ANDROID_NDK_HOME:-}" ]]; then
    # Use the NDK's real, VM-neutral JNI interface without shadowing host libc headers.
    mkdir -p "$test_dir/jni"
    cp "$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include/jni.h" "$test_dir/jni/jni.h"
    cc -std=gnu11 "${flags[@]}" -I "$native_dir/tests/include" -I "$test_dir/jni" \
        "$native_dir/tests/jni_gl_start_test.c" -o "$test_dir/jni_test"
    "$test_dir/jni_test"
    cc -std=gnu11 "${flags[@]}" -DJNINativeInterface_=JNINativeInterface \
        -I "$test_dir/jni" -I "$native_dir" \
        "$native_dir/tests/exception_inspect_test.c" "$native_dir/exception_inspect.c" \
        -pthread -o "$test_dir/exception_test"
    "$test_dir/exception_test"
    cc -std=gnu11 "${flags[@]}" -I "$test_dir/jni" -I "$native_dir" \
        "$native_dir/tests/input_trace_test.c" "$native_dir/input_trace.c" \
        -o "$test_dir/input_test"
    "$test_dir/input_test"
else
    echo "SKIP typed JNI test: set ANDROID_NDK_HOME to run against its real JNI header"
fi
