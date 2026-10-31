#!/usr/bin/env python3
"""Apply the pinned engine's Android GL-version and native-stack settings.

GLForceDLLVersion=0x0101 avoids the original pre-context version probe.
StackSwitch=1 enables the supplied runtime's existing native import/callback
veneers. The game always starts on an allocated fibre stack, even when this
switching is disabled; Java callbacks must return to the Android thread stack.

Pinned evidence: s3eExecStartGame0x1946c creates a fibre; FibreSwitch_asm0x2e4a0
replaces SP. StackSwitchReadConfig0x3c944 reads this setting, and external import
relocation paths0x173e2/0x17572 select stack-switch veneers when enabled.
The source s3e.icf's global StackSwitch=0 is a development default, not a guard
against allocating the game fibre. The Android-only override below preserves
all other configuration bytes and does not enlarge or remove the game stack.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ORIGINAL_SHA256 = "aa22d6f73e5094d51a1138d6fdf73405ac0ed49bc625bdf4d4a7d3d4a27d36a8"
ANDROID_OVERRIDE = (
    b"\r\n# S3CE: GLES version and native-thread stack callbacks on Android.\r\n"
    b"{OS=ANDROID}\r\n[S3E]\r\nGLForceDLLVersion=0x0101\r\nStackSwitch=1\r\n{}\r\n"
)


def patched_bytes(original: bytes) -> bytes:
    """Accept only the pinned original or this module's exact patched result."""
    source = original
    if original.endswith(ANDROID_OVERRIDE):
        source = original[:-len(ANDROID_OVERRIDE)]
    if hashlib.sha256(source).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("Unexpected app.icf bytes; refusing the Android runtime configuration patch")
    return source + ANDROID_OVERRIDE


def apply(decoded: Path) -> bool:
    target = decoded / "assets" / "app.icf.jpg"
    original = target.read_bytes()
    result = patched_bytes(original)
    if result == original:
        return False
    target.write_bytes(result)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decoded", type=Path)
    args = parser.parse_args()
    print("Android GL/native-stack configuration: " + ("patched" if apply(args.decoded) else "already patched"))
