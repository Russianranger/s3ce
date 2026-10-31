package com.ideaworks3d.thesims3;

import android.app.Activity;
import android.app.ActivityManager;
import android.app.Application;
import android.content.Context;
import android.content.pm.PackageInfo;
import android.os.Build;
import android.os.Debug;
import android.os.Bundle;
import android.os.Process;
import android.os.SystemClock;
import android.util.Log;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;

/** Attribution starts before any Activity, native bootstrap or engine exit. */
public final class GameSession {
    private static SessionDiagnostics diagnostics;
    private GameSession() { }

    public static String processName() {
        if (Build.VERSION.SDK_INT >= 28) {
            try { return Application.getProcessName(); }
            catch (Throwable error) { return null; }
        }
        // ApplicationInfo describes the default process even from :launcher.
        try (FileInputStream input = new FileInputStream("/proc/self/cmdline")) {
            byte[] bytes = new byte[256];
            int count = input.read(bytes);
            int end = 0;
            while (end < count && bytes[end] != 0) end++;
            return new String(bytes, 0, end, StandardCharsets.UTF_8);
        } catch (Throwable error) { return null; }
    }

    public static String buildIdentity(Context context) {
        try {
            PackageInfo info = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
            long code = Build.VERSION.SDK_INT >= 28 ? info.getLongVersionCode() : info.versionCode;
            return "package=" + context.getPackageName() + " version=" + info.versionName + " code=" + code
                    + " firstInstallMs=" + info.firstInstallTime + " lastUpdateMs=" + info.lastUpdateTime;
        } catch (Throwable error) { return "package=" + context.getPackageName() + " version=unknown metadataError=" + error; }
    }

    public static String versionLabel(Context context) {
        try {
            PackageInfo info = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
            long code = Build.VERSION.SDK_INT >= 28 ? info.getLongVersionCode() : info.versionCode;
            return "Compatibility build " + info.versionName + " (" + code + ")";
        } catch (Throwable error) { return "Compatibility build (version unavailable)"; }
    }

    public static synchronized void initialize(Application application, String process) {
        if (diagnostics != null || !application.getPackageName().equals(process)) return;
        diagnostics = new SessionDiagnostics(application.getFilesDir());
        try {
            diagnostics.begin(buildIdentity(application) + " process=" + process
                    + " process64=" + Process.is64Bit(), System.currentTimeMillis(),
                    SystemClock.elapsedRealtime(), Process.myPid());
        } catch (Exception error) { Log.e("S3CECompat", "Could not persist session identity", error); }
        phase("Application.onCreate");
        memory(application, "process-start");
        application.registerActivityLifecycleCallbacks(new Application.ActivityLifecycleCallbacks() {
            private void activity(Activity activity, String phase) {
                GameSession.phase("Activity " + activity.getClass().getName() + " " + phase);
            }
            public void onActivityCreated(Activity activity, Bundle state) { activity(activity, "created restored=" + (state != null)); }
            public void onActivityStarted(Activity activity) { activity(activity, "started"); }
            public void onActivityResumed(Activity activity) { activity(activity, "resumed"); }
            public void onActivityPaused(Activity activity) { activity(activity, "paused"); }
            public void onActivityStopped(Activity activity) { activity(activity, "stopped"); }
            public void onActivitySaveInstanceState(Activity activity, Bundle state) { activity(activity, "save-instance-state"); }
            public void onActivityDestroyed(Activity activity) { activity(activity, "destroyed finishing=" + activity.isFinishing()); }
        });
    }

    public static synchronized void phase(String phase) {
        if (diagnostics == null) return;
        try { diagnostics.phase(phase, System.currentTimeMillis(), SystemClock.elapsedRealtime()); }
        catch (Throwable error) {
            try { Log.e("S3CECompat", "Could not persist session phase", error); }
            catch (Throwable ignored) { }
        }
    }

    /** A few explicit startup checkpoints, never a per-frame allocation/query. */
    public static void memory(Context context, String checkpoint) {
        try {
            ActivityManager manager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
            ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo();
            manager.getMemoryInfo(memory);
            Runtime runtime = Runtime.getRuntime();
            phase("MEMORY checkpoint=" + checkpoint + " availBytes=" + memory.availMem
                    + " totalBytes=" + memory.totalMem + " thresholdBytes=" + memory.threshold
                    + " lowMemory=" + memory.lowMemory + " processPssKiB=" + Debug.getPss()
                    + " javaUsedBytes=" + (runtime.totalMemory() - runtime.freeMemory())
                    + " javaMaxBytes=" + runtime.maxMemory());
        } catch (Throwable error) {
            try { phase("MEMORY checkpoint=" + checkpoint + " unavailable=" + error); }
            catch (Throwable ignored) { }
        }
    }

    public static void appendReport(Context context, StringBuilder report) {
        SessionDiagnostics.appendReport(context.getFilesDir(), report);
    }
}
