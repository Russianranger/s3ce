#!/usr/bin/env bash
set -euo pipefail
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to an Android NDK r28 or newer directory}"
native_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
output="${1:-$native_dir/build/libairplay.so}"
mkdir -p -- "$(dirname -- "$output")"
object_dir="$(mktemp -d)"
trap 'python3 -c '\''import shutil,sys; shutil.rmtree(sys.argv[1])'\'' "$object_dir"' EXIT
compiler="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi26-clang"
cxx="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi26-clang++"
common=(-fPIC -mthumb -O2 -Wall -Wextra -Werror -fvisibility=hidden -fstack-protector-strong)
"$compiler" "${common[@]}" -c "$native_dir/legacy_loader.c" -o "$object_dir/loader.o"
"$compiler" "${common[@]}" -c "$native_dir/graphics_diagnostics.c" -o "$object_dir/graphics.o"
"$compiler" "${common[@]}" -c "$native_dir/graphics_safety.c" -o "$object_dir/safety.o"
"$cxx" "${common[@]}" -std=c++14 -fno-rtti -fexceptions -c \
    "$native_dir/pvrtc/PVRTDecompress.cpp" -o "$object_dir/pvrtc.o"
"$cxx" "${common[@]}" -std=c++14 -fno-rtti -fexceptions -c \
    "$native_dir/pvrtc/pvrtc_bridge.cpp" -o "$object_dir/bridge.o"
"$cxx" -shared -static-libstdc++ "${common[@]}" \
    -Wl,-z,relro,-z,now,-z,noexecstack -Wl,-soname,libairplay.so \
    "$object_dir/loader.o" "$object_dir/graphics.o" "$object_dir/safety.o" "$object_dir/pvrtc.o" "$object_dir/bridge.o" \
    -llog -landroid -ldl -lEGL -o "$output"
echo "$output"
