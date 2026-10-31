package com.ideaworks3d.thesims3;

import android.app.Application;
import android.os.Build;
import android.os.Process;
import java.io.File;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/** Preserve Java exceptions before Android's ordinary crash handler terminates. */
public final class CrashCaptureApplication extends Application {
    @Override public void onCreate() {
        super.onCreate();
        final Thread.UncaughtExceptionHandler normal = Thread.getDefaultUncaughtExceptionHandler();
        String process = Build.VERSION.SDK_INT >= 28 ? Application.getProcessName() : getPackageName();
        final File output = new File(getFilesDir(), process != null && process.endsWith(":launcher")
                ? "compat-java-launcher.log" : "compat-java-crash.log");
        Thread.setDefaultUncaughtExceptionHandler((thread, error) -> {
            try {
                StringWriter text = new StringWriter();
                text.append("S3CE 0.1.5 Java crash pid=" + Process.myPid()
                        + " time=" + System.currentTimeMillis() + " thread=" + thread.getName() + "\n");
                error.printStackTrace(new PrintWriter(text));
                Files.write(output.toPath(), text.toString().getBytes(StandardCharsets.UTF_8));
            } catch (Throwable ignored) { }
            finally {
                if (normal != null) normal.uncaughtException(thread, error);
                else { Process.killProcess(Process.myPid()); System.exit(10); }
            }
        });
    }
}
