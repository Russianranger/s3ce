package com.ideaworks3d.thesims3;

import android.app.Activity;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.Gravity;
import android.view.MotionEvent;
import android.widget.Button;
import android.widget.FrameLayout;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/** Small frame/input breadcrumbs and a watchdog that does not call the engine. */
public final class GameDiagnostics {
    private static final AtomicLong frames = new AtomicLong();
    private static final AtomicLong touches = new AtomicLong();
    private static volatile String lastTouch = "none";
    private static volatile long uiHeartbeat;
    private static volatile File logFile;
    private static boolean started;
    private static long lastDump;
    private static final ScheduledExecutorService worker = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "S3CE-Watchdog"); t.setDaemon(true); return t;
    });

    public static void openReports(Activity activity) {
        Intent report = new Intent(activity, CompatActivity.class);
        report.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
        activity.startActivity(report);
    }

    public static void attach(final Activity activity) {
        logFile = new File(activity.getFilesDir(), "compat-events.log");
        Button report = new Button(activity);
        report.setText("Report");
        report.setTextSize(11);
        report.setAlpha(0.8f);
        report.setOnClickListener(v -> openReports(activity));
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.TOP | Gravity.RIGHT);
        activity.addContentView(report, params);
        startWatchdog();
    }

    public static void frame() { frames.incrementAndGet(); }

    public static void touch(MotionEvent event) {
        // Copy values now; Android recycles MotionEvent after dispatch.
        touches.incrementAndGet();
        int count = event.getPointerCount();
        lastTouch = "action=" + event.getActionMasked() + " pointers=" + count
                + (count > 0 ? " x=" + (int) event.getX(0) + " y=" + (int) event.getY(0) : "");
    }

    private static synchronized void startWatchdog() {
        if (started) return;
        started = true;
        Handler main = new Handler(Looper.getMainLooper());
        uiHeartbeat = SystemClock.elapsedRealtime();
        append("\nGame process " + android.os.Process.myPid() + " started\n");
        worker.scheduleAtFixedRate(() -> {
            try {
                long now = SystemClock.elapsedRealtime();
                long age = now - uiHeartbeat;
                append("time=" + now + " frames=" + frames.get() + " touches=" + touches.get()
                        + " uiAgeMs=" + age + " " + lastTouch + "\n");
                if (age > 6000 && now - lastDump > 15000) {
                    lastDump = now;
                    StringBuilder dump = new StringBuilder("UI stalled; Java stacks:\n");
                    for (Map.Entry<Thread, StackTraceElement[]> entry : Thread.getAllStackTraces().entrySet()) {
                        boolean relevant = entry.getKey().getName().equals("main");
                        for (StackTraceElement frame : entry.getValue())
                            relevant |= frame.getClassName().startsWith("com.ideaworks3d.airplay");
                        if (!relevant) continue;
                        dump.append(entry.getKey().getName()).append(' ')
                                .append(entry.getKey().getState()).append('\n');
                        int count = 0;
                        for (StackTraceElement frame : entry.getValue()) {
                            if (count++ == 24) break;
                            dump.append("  ").append(frame).append('\n');
                        }
                    }
                    append(dump.toString());
                }
                main.post(() -> uiHeartbeat = SystemClock.elapsedRealtime());
            } catch (Throwable ignored) { }
        }, 0, 2, TimeUnit.SECONDS);
    }

    private static void append(String message) {
        File target = logFile;
        if (target == null) return;
        try (FileOutputStream stream = new FileOutputStream(target, target.length() < 131072)) {
            stream.write(message.getBytes(StandardCharsets.UTF_8));
        } catch (Exception ignored) { }
    }
}
