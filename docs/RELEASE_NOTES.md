S3CE 0.1.3 — targeted fix for the reported startup crash.

The 0.1.2 report identifies SIGSEGV in glGetString(GL_VERSION), called by the
original engine before Java has created an EGL context. Both rendering modes
failed at the same original wrapper, so texture conversion was not the failing
operation in that trace.

Changes:

- Use the engine's existing Android [S3E] GLForceDLLVersion=0x0101 setting to
  select its GLES1.1 path without the premature version probe.
- Guard the original GL string wrapper in both modes. Without a current context,
  return NULL before entering the GLES driver. Once a context is current, pass
  through the normal query and preserve the original extension filtering.
- Keep PVRTC texture conversion, touch corrections, and the working report
  save/share/view options. The earlier alpha workaround stays disabled.

The fix matches the captured crash path and passes native no-context/current-
context regression tests, ARM compilation, independent review, and packaging
checks. The updated game still needs device confirmation.

Test:

1. Install over 0.1.2. Do not uninstall or clear app data.
2. Open The Sims 3 CE and **uncheck Original rendering (diagnostic mode)**.
   Your last test enabled it; that setting can persist through the update.
3. Tap Start game and check whether the menu loads. Check backgrounds, hair/eyes
   and the room, then swipe across the Sim in Create-a-Sim.
4. If it works, proceed into the house and save/reopen when convenient.
5. If it crashes or stalls, reopen the app icon, use Save report, and attach the
   .txt file. Report saving worked on the previous test and is retained.

Same app ID, signing certificate, saved-data location, ARM32 and 4 KiB page
requirements. No new game-file import is needed.
