#!/usr/bin/env python3
"""Use the supplied engine's GLES 1.1 setting to avoid its pre-context GL probe.

Evidence from the pinned ARM32 Airplay library (unmodified file offsets):
* s3eGLDetermineGLVersion (0x33a80) queries "GLForceDLLVersion" at 0x33a9c.
  The key literal is at 0x480c4. A nonzero value is stored at 0x33aa8 and
  returned without calling glGetString(GL_VERSION) at 0x33acc.
* s3eConfigGet (0x2972c) uses section "s3e" (literal 0x43690).
* s3eGLGetInt_platform calls this probe at 0x3f690 before Java GL startup
  can create a current context. The supplied s3e.icf already demonstrates
  GLForceDLLVersion=0x0101 for an older device.

The override selects the game's GLES 1.1 path; it does not fabricate driver
extensions or change texture assets. This is a version-specific startup fix
candidate. Static evidence does not establish successful Android gameplay.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ORIGINAL_SHA256 = "aa22d6f73e5094d51a1138d6fdf73405ac0ed49bc625bdf4d4a7d3d4a27d36a8"
ANDROID_OVERRIDE = (
    b"\r\n# S3CE: select GLES 1.1 before a GL context exists.\r\n"
    b"{OS=ANDROID}\r\n[S3E]\r\nGLForceDLLVersion=0x0101\r\n{}\r\n"
)


def patched_bytes(original: bytes) -> bytes:
    """Accept only the pinned original or this module's exact patched result."""
    source = original
    if original.endswith(ANDROID_OVERRIDE):
        source = original[:-len(ANDROID_OVERRIDE)]
    if hashlib.sha256(source).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("Unexpected app.icf bytes; refusing the GLES version configuration patch")
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
    print("Android GLES version configuration: " + ("patched" if apply(args.decoded) else "already patched"))
