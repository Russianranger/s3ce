#!/usr/bin/env python3
"""Enable the supplied game's existing Snapdragon alpha-state workaround on Android.

The source app.icf only enables this on named Windows Mobile Snapdragon devices.
The preserved S3E program reads Game/SnapdragonAlphaWorkaround into global
0x4a166b80 at unpacked offset 0x14638c. Its GL_ALPHA_TEST enable path checks
that flag at 0xbce00 and issues the game's existing driver-state flush.
This changes no textures, executable bytes, or non-Android configuration.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ORIGINAL_SHA256 = "aa22d6f73e5094d51a1138d6fdf73405ac0ed49bc625bdf4d4a7d3d4a27d36a8"
ANDROID_OVERRIDE = (
    b"\r\n# S3CE: use the game's existing Snapdragon alpha-state workaround.\r\n"
    b"{OS=ANDROID}\r\n[Game]\r\nSnapdragonAlphaWorkaround=1\r\n{}\r\n"
)


def patched_bytes(original: bytes) -> bytes:
    """Accept the pinned original or this exact idempotent patched result."""
    source = original
    if original.endswith(ANDROID_OVERRIDE):
        source = original[:-len(ANDROID_OVERRIDE)]
    if hashlib.sha256(source).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("Unexpected app.icf bytes; refusing the graphics configuration patch")
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
    print("Android Snapdragon alpha workaround: " + ("patched" if apply(args.decoded) else "already patched"))
