package com.ideaworks3d.thesims3;

import android.app.Activity;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
import android.widget.Button;
import android.widget.FrameLayout;
import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
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
    private static final AtomicLong touchDowns = new AtomicLong();
    private static final AtomicLong touchMoves = new AtomicLong();
    private static final AtomicLong touchUps = new AtomicLong();
    private static final AtomicLong touchCancels = new AtomicLong();
    private static final AtomicLong touchBlocked = new AtomicLong();
    private static volatile String lastTouch = "none";
    private static volatile long uiHeartbeat;
    private static volatile File logFile;
    private static volatile File glLogFile;
    private static final Object glLogLock = new Object();
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
        glLogFile = new File(activity.getFilesDir(), "compat-java-gl.log");
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

    public static void recordGlEntry(int version, boolean useGl, Object paused, Object terminating) {
        recordGlState("ENTRY", version, useGl, paused, terminating);
    }

    public static void recordGlExit(int version, boolean useGl, Object paused, Object terminating) {
        recordGlState("EXIT", version, useGl, paused, terminating);
    }

    private static void recordGlState(String phase, int version, boolean useGl,
                                      Object paused, Object terminating) {
        try {
            Thread thread = Thread.currentThread();
            appendGl("Java GL bridge " + phase + " version=" + version + " useGL=" + useGl
                    + " paused=" + String.valueOf(paused) + " terminating=" + String.valueOf(terminating)
                    + " javaThread=" + thread.getId() + " name=" + thread.getName() + "\n");
        } catch (Throwable error) { glLogFailure(error); }
    }

    /** Called before rethrowing the same Java exception through the JNI bridge. */
    public static void recordGlFailure(Throwable failure) {
        try {
            StringWriter trace = new StringWriter();
            trace.append("Java GL bridge FAILURE thread=" + Thread.currentThread().getName() + "\n");
            if (failure != null) failure.printStackTrace(new PrintWriter(trace));
            else trace.append("No Throwable supplied\n");
            appendGl(trace.toString());
        } catch (Throwable error) { glLogFailure(error); }
    }

    private static void glLogFailure(Throwable error) {
        try { Log.e("S3CECompat", "Could not persist Java GL bridge diagnostics", error); }
        catch (Throwable ignored) { }
    }

    private static void appendGl(String message) throws java.io.IOException {
        Log.i("S3CECompat", message.substring(0, message.indexOf('\n') < 0
                ? message.length() : message.indexOf('\n')));
        File target = glLogFile;
        if (target == null) throw new java.io.IOException("Game GL log directory is not initialized");
        synchronized (glLogLock) {
            try (FileOutputStream output = new FileOutputStream(target, target.length() < 131072)) {
                output.write(("time=" + System.currentTimeMillis() + " " + message)
                        .getBytes(StandardCharsets.UTF_8));
                output.getFD().sync();
            }
        }
    }

    public static void touch(MotionEvent event) {
        touch(event, false);
    }

    public static void touch(MotionEvent event, boolean inputTextRunning) {
        // Copy values now; Android recycles MotionEvent after dispatch.
        touches.incrementAndGet();
        int action = event.getActionMasked();
        if (action == MotionEvent.ACTION_DOWN || action == MotionEvent.ACTION_POINTER_DOWN)
            touchDowns.incrementAndGet();
        else if (action == MotionEvent.ACTION_MOVE) touchMoves.incrementAndGet();
        else if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_POINTER_UP)
            touchUps.incrementAndGet();
        else if (action == MotionEvent.ACTION_CANCEL) touchCancels.incrementAndGet();
        boolean blocked = inputTextRunning && action != MotionEvent.ACTION_CANCEL;
        if (blocked) touchBlocked.incrementAndGet();
        int count = event.getPointerCount();
        lastTouch = "action=" + action + " pointers=" + count
                + " source=0x" + Integer.toHexString(event.getSource())
                + (count > 0 ? " id=" + event.getPointerId(0) + " x=" + (int) event.getX(0)
                        + " y=" + (int) event.getY(0) : "")
                + " inputText=" + inputTextRunning + " blocked=" + blocked;
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
                        + " down=" + touchDowns.get() + " move=" + touchMoves.get()
                        + " up=" + touchUps.get() + " cancel=" + touchCancels.get()
                        + " blocked=" + touchBlocked.get() + " uiAgeMs=" + age + " " + lastTouch + "\n");
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
