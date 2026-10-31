S3CE 0.1.9 — indexed HUD rendering candidate.

Startup, reopening, hint dismissal, rotation and character-option changes now
work on the Thor. The remaining problem is missing HUD panels and controls.

This update changes the shared HUD quad to explicit indices 0, 1, 2, 3. It preserves
the original vertices, texture coordinates, textures, shapes and hit targets,
while using the indexed draw API already used by visible 3D models. All other
archive payloads remain byte-identical. Host ARM execution and pixel comparisons
pass; whether this restores the Thor's UI still needs a device test.

Reports also capture bounded GPU state around matching quad draws. The working
RAM, stack, PVRTC and input behavior remains.

Test:

1. Install over 0.1.8 without uninstalling or clearing app data.
2. Leave Original rendering (diagnostic mode) **unchecked**, then Start game.
3. Check whether the welcome hint has a visible panel and close control. Dismiss
   it and check the appearance tabs, clothing buttons and traits controls.
4. If anything is still missing, save the report from that run and send it with
   a screenshot. The report now records the live GPU state for these draw shapes.

If the welcome control is still invisible, the previous tap near (500, 370) on the
1920×1080 screen can still be used; release and wait one second before swiping.

Same application ID, signing key and data location. Requires ARM32 application
support and 4 KiB memory pages. No hardware UI recovery is claimed yet.
