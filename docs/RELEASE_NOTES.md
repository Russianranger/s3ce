S3CE 0.1.6 — restore the Android thread stack for native service callbacks.

The 0.1.5 report showed that both GL startup and its Java error logger failed
before entering Java. The freshly resolved and cached method IDs matched, so
that run did not support a stale-method-ID explanation.

Binary inspection and ARM execution tests found the runtime always starts the
game on an allocated fibre stack. Its supplied StackSwitch=0 setting disables
the native service veneers that return callbacks to the Android thread stack.
Android ART checks stack bounds before entering Java; the foreign stack explains
why even the error logger can be rejected before its first line.

This update enables the engine's existing stack-switch veneers and uses its
original stack-switch mechanism for early GL initialization when entered from
the game fibre. Java runs on the original Android thread stack, on the same OS
thread. The game stack is restored afterward, and the actual window EGL context
remains bound to that thread. No temporary context is used.

The full executable allocation is flushed through the original permission/cache
routine before generated stack-switch stubs execute. The original flush covered
only the rounded core code extent, leaving part of the enabled stub area outside
its range; this update preserves its permission and return-value behavior.

Native diagnostics also classify common Java failures without calling a Java
method, and record the native stack bounds. This keeps a failed Java logger
from hiding the exception type.

Checks passed: compiled ARM bridge/original-trampoline execution with callback
re-entry and register/stack restoration, six native sanitizer suites, native
Throwable identity preservation, code/stub flush coverage, ARM import/relocation
and asset/configuration checks, APK signatures, and exact release reconstruction.

Test:

1. Install over the current app without uninstalling or clearing data.
2. Leave Original rendering (diagnostic mode) **unchecked**, then Start game.
3. If the menu loads, check backgrounds/hair/eyes and Create-a-Sim swipes, then
   enter the house and save/reopen.
4. If startup fails, reopen the app icon and Save report.

Same app ID, signing key and data location. ARM32 and 4 KiB requirements remain.
Hardware startup and gameplay are still unverified for this update.
