package com.ideaworks3d.thesims3;

import android.app.ActivityManager;
import android.app.ApplicationExitInfo;
import android.content.Context;
import android.os.Build;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

/** Own-package exit history can retain the previous build's native crash. */
public final class ExitReport {
    public static void append(Context context, StringBuilder report) {
        if (Build.VERSION.SDK_INT < 30) return;
        report.append("\nAndroid process exit history:\n");
        report.append("Exit records survive APK updates. Match PID/time to session identity before attributing a failure.\n");
        try {
            ActivityManager manager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
            List<ApplicationExitInfo> history = manager.getHistoricalProcessExitReasons(context.getPackageName(), 0, 20);
            int shown = 0;
            boolean traced = false;
            for (ApplicationExitInfo exit : history) {
                if (exit.getProcessName().endsWith(":launcher")) continue;
                report.append("process=").append(exit.getProcessName()).append(" pid=").append(exit.getPid())
                        .append(" time=").append(exit.getTimestamp()).append(" reason=").append(exit.getReason())
                        .append('(').append(reasonName(exit.getReason())).append(')')
                        .append(" status=").append(exit.getStatus()).append(" description=").append(exit.getDescription())
                        .append(" rssKB=").append(exit.getRss()).append('\n');
                if (!traced && (exit.getReason() == ApplicationExitInfo.REASON_CRASH_NATIVE
                        || exit.getReason() == ApplicationExitInfo.REASON_ANR)) {
                    try (InputStream stream = exit.getTraceInputStream()) {
                        if (stream != null) {
                            int limit = exit.getReason() == ApplicationExitInfo.REASON_CRASH_NATIVE ? 2 * 1024 * 1024 : 24576;
                            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                            byte[] buffer = new byte[8192];
                            int count;
                            while (bytes.size() < limit && (count = stream.read(buffer, 0,
                                    Math.min(buffer.length, limit - bytes.size()))) > 0) bytes.write(buffer, 0, count);
                            report.append("Trace for pid ").append(exit.getPid()).append(":\n");
                            report.append(exit.getReason() == ApplicationExitInfo.REASON_CRASH_NATIVE
                                    ? NativeTombstoneSummary.summarize(bytes.toByteArray())
                                    : new String(bytes.toByteArray(), StandardCharsets.UTF_8));
                            if (bytes.size() == limit) report.append("\n[Trace reached read limit]\n");
                            traced = true;
                        }
                    } catch (Exception error) { report.append("Trace unavailable: ").append(error).append('\n'); }
                }
                if (++shown == 8) break;
            }
            if (shown == 0) report.append("No retained game-process exits.\n");
        } catch (Exception error) { report.append("Exit history unavailable: ").append(error).append('\n'); }
    }

    static String reasonName(int reason) {
        switch (reason) {
            case ApplicationExitInfo.REASON_UNKNOWN: return "UNKNOWN";
            case ApplicationExitInfo.REASON_EXIT_SELF: return "EXIT_SELF";
            case ApplicationExitInfo.REASON_SIGNALED: return "SIGNALED";
            case ApplicationExitInfo.REASON_LOW_MEMORY: return "LOW_MEMORY";
            case ApplicationExitInfo.REASON_CRASH: return "CRASH";
            case ApplicationExitInfo.REASON_CRASH_NATIVE: return "CRASH_NATIVE";
            case ApplicationExitInfo.REASON_ANR: return "ANR";
            case ApplicationExitInfo.REASON_INITIALIZATION_FAILURE: return "INITIALIZATION_FAILURE";
            case ApplicationExitInfo.REASON_PERMISSION_CHANGE: return "PERMISSION_CHANGE";
            case ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE: return "EXCESSIVE_RESOURCE_USAGE";
            case ApplicationExitInfo.REASON_USER_REQUESTED: return "USER_REQUESTED";
            case ApplicationExitInfo.REASON_USER_STOPPED: return "USER_STOPPED";
            case ApplicationExitInfo.REASON_DEPENDENCY_DIED: return "DEPENDENCY_DIED";
            case ApplicationExitInfo.REASON_OTHER: return "OTHER";
            default: return "UNRECOGNIZED";
        }
    }
}
