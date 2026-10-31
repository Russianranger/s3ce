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
else
    echo "SKIP typed JNI test: set ANDROID_NDK_HOME to run against its real JNI header"
fi
