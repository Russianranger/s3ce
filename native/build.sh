#!/usr/bin/env bash
set -euo pipefail
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to an Android NDK r28 or newer directory}"
native_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
output="${1:-$native_dir/build/libairplay.so}"
mkdir -p -- "$(dirname -- "$output")"
compiler="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/armv7a-linux-androideabi26-clang"
"$compiler" -shared -fPIC -mthumb -O2 -Wall -Wextra -Werror \
    -fvisibility=hidden -fstack-protector-strong \
    -Wl,-z,relro,-z,now,-z,noexecstack -Wl,-soname,libairplay.so \
    "$native_dir/legacy_loader.c" -llog -landroid -ldl -o "$output"
echo "$output"
