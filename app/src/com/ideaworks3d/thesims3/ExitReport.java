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
        try {
            ActivityManager manager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
            List<ApplicationExitInfo> history = manager.getHistoricalProcessExitReasons(context.getPackageName(), 0, 20);
            int shown = 0;
            boolean traced = false;
            for (ApplicationExitInfo exit : history) {
                if (exit.getProcessName().endsWith(":launcher")) continue;
                report.append("process=").append(exit.getProcessName()).append(" pid=").append(exit.getPid())
                        .append(" time=").append(exit.getTimestamp()).append(" reason=").append(exit.getReason())
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
}
