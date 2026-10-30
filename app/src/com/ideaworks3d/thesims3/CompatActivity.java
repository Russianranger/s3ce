package com.ideaworks3d.thesims3;

import android.app.Activity;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Process;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.File;
import java.io.ByteArrayOutputStream;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.concurrent.TimeUnit;

/** Starts the preserved engine only after an observable compatibility check. */
public final class CompatActivity extends Activity {
    private String lastError = "";
    private TextView status;

    public static void keepScreenOn(final Activity activity) {
        activity.runOnUiThread(() -> activity.getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON));
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (24 * getResources().getDisplayMetrics().density);
        layout.setPadding(pad, pad, pad, pad);
        layout.setBackgroundColor(0xff12202b);
        status = new TextView(this);
        status.setTextColor(0xffeeeeee);
        status.setTextSize(18);
        status.setText("The Sims 3 CE\nCompatibility build 0.1.1\n\n"
                + "Touch controls. Saves stay on this device.\n"
                + "Reopen this app to share a report if the game freezes.\n");
        layout.addView(status);
        Button play = new Button(this);
        play.setText("Start game");
        play.setOnClickListener(v -> startGame());
        layout.addView(play);
        Button diagnostics = new Button(this);
        diagnostics.setText("Share diagnostics");
        diagnostics.setOnClickListener(v -> shareReport(diagnostics));
        layout.addView(diagnostics);
        setContentView(layout);
        // This Activity lives in a separate process/task. Never auto-enter a
        // frozen game when the user reopens the launcher for its diagnostics.
    }

    private void startGame() {
        Intent game = new Intent(this, GameBootActivity.class);
        game.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(game);
    }

    private void shareReport(final Button button) {
        button.setEnabled(false);
        status.setText("Preparing diagnostic report…");
        Thread worker = new Thread(() -> {
            final String details = report();
            runOnUiThread(() -> {
                button.setEnabled(true);
                status.setText("Report ready. Use Start game to return to the game.");
                Intent send = new Intent(Intent.ACTION_SEND);
                send.setType("text/plain");
                send.putExtra(Intent.EXTRA_SUBJECT, "S3CE compatibility diagnostics");
                send.putExtra(Intent.EXTRA_TEXT, details);
                startActivity(Intent.createChooser(send, "Share S3CE diagnostics"));
            });
        }, "S3CE-Report");
        worker.setDaemon(true);
        worker.start();
    }

    private String report() {
        StringBuilder text = new StringBuilder("S3CE 0.1.1 diagnostic report\n");
        text.append("Android: ").append(Build.VERSION.RELEASE).append(" API ")
                .append(Build.VERSION.SDK_INT).append("\nDevice: ")
                .append(Build.MANUFACTURER).append(' ').append(Build.MODEL)
                .append("\nABIs: ").append(Arrays.toString(Build.SUPPORTED_ABIS))
                .append("\nProcess64: ").append(Process.is64Bit()).append('\n');
        text.append(lastError);
        for (String name : new String[]{"compat-native.log", "compat-events.log", "compat-boot.log"}) {
            File log = new File(getFilesDir(), name);
            try (RandomAccessFile input = new RandomAccessFile(log, "r")) {
                int length = (int) Math.min(input.length(), 32768);
                input.seek(input.length() - length);
                byte[] bytes = new byte[length];
                input.readFully(bytes);
                text.append('\n').append(name).append(":\n")
                        .append(new String(bytes, StandardCharsets.UTF_8));
            } catch (Exception error) { text.append("\n").append(name).append(": ").append(error); }
        }
        java.lang.Process logcat = null;
        try {
            logcat = new ProcessBuilder("logcat", "-d", "-v", "threadtime", "-t", "300",
                    "S3CECompat:I", "AirplayActivity:I", "AirplayThread:I", "AndroidRuntime:E", "*:S")
                    .redirectErrorStream(true).start();
            final java.lang.Process process = logcat;
            ByteArrayOutputStream captured = new ByteArrayOutputStream();
            Thread drain = new Thread(() -> {
                byte[] buffer = new byte[4096];
                try {
                    int count;
                    while ((count = process.getInputStream().read(buffer)) > 0) {
                        synchronized (captured) {
                            int keep = Math.min(count, Math.max(0, 32768 - captured.size()));
                            captured.write(buffer, 0, keep);
                        }
                    }
                } catch (Exception ignored) { }
            }, "S3CE-Logcat");
            drain.setDaemon(true);
            drain.start();
            if (!logcat.waitFor(2, TimeUnit.SECONDS)) logcat.destroyForcibly();
            drain.join(500);
            synchronized (captured) {
                text.append("\nRecent app logcat:\n")
                        .append(new String(captured.toByteArray(), StandardCharsets.UTF_8));
            }
        } catch (Exception error) { text.append("\nLogcat unavailable: ").append(error); }
        finally { if (logcat != null) logcat.destroy(); }
        if (text.length() > 96 * 1024)
            return text.substring(0, 96 * 1024) + "\n[Report truncated to fit sharing limits]\n";
        return text.toString();
    }
}
