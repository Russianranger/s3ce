# Bootstrap host boundaries

`verify_boot_host.py` compiles the production `RuntimeBootstrap` and
`GameBootActivity` Java, then runs each scenario in a fresh JVM. It checks single
and concurrent initialization, cached failure, reentry, rendering-mode conflict,
per-Activity admission, preserved Main intent/flags, diagnostics UI and the
unavailable-library failure path. The private runtime is primed only in the
explicit ready-state host scenarios; this does not run an Android game, restore
a physical process, or modify game saves/memory.

Android Activity/View/Intent/files, existing rendering preferences and diagnostic
callbacks are small declared doubles. Positive legacy JNI registration remains
an Android execution requirement. The missing-library scenarios exercise real
`System.loadLibrary` failure on the host, preserving its exception in the
production failure UI/log. Assembled original onCreate/onStart control flow is
checked separately by `verify_boot.py`.
