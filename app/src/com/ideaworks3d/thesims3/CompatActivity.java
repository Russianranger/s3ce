package com.ideaworks3d.thesims3;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Process;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.File;
import java.io.ByteArrayOutputStream;
import java.io.RandomAccessFile;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.concurrent.TimeUnit;

/** Starts the preserved engine only after an observable compatibility check. */
public final class CompatActivity extends Activity {
    private static final int SAVE_REPORT = 72;
    private TextView status;
    private CheckBox originalRendering;
    private Button[] reportButtons;
    private String pendingReport;

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
        status.setText("The Sims 3 CE\nCompatibility build 0.1.3\n\n"
                + "Touch controls. Saves stay on this device.\n"
                + "Save a report before retrying a crashed game.\n");
        layout.addView(status);
        originalRendering = new CheckBox(this);
        originalRendering.setText("Original rendering (diagnostic mode)");
        originalRendering.setTextColor(0xffeeeeee);
        originalRendering.setChecked(getPreferences(MODE_PRIVATE).getBoolean("original_rendering", false));
        originalRendering.setOnCheckedChangeListener((button, checked) ->
                getPreferences(MODE_PRIVATE).edit().putBoolean("original_rendering", checked).apply());
        layout.addView(originalRendering);
        Button play = new Button(this);
        play.setText("Start game");
        play.setOnClickListener(v -> startGame());
        layout.addView(play);
        String[] labels = {"Save report", "Share report file", "View / copy report"};
        reportButtons = new Button[labels.length];
        for (int i = 0; i < labels.length; i++) {
            final int action = i;
            Button button = new Button(this);
            button.setText(labels[i]);
            button.setOnClickListener(v -> prepareReport(action));
            reportButtons[i] = button;
            layout.addView(button);
        }
        ScrollView scrolling = new ScrollView(this);
        scrolling.addView(layout);
        setContentView(scrolling);
        if (state != null) pendingReport = state.getString("pending_report");
        // This Activity lives in a separate process/task. Never auto-enter a
        // frozen game when the user reopens the launcher for its diagnostics.
    }

    private void startGame() {
        Intent game = new Intent(this, GameBootActivity.class);
        game.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        game.putExtra("graphics_compatibility", !originalRendering.isChecked());
        startActivity(game);
    }

    private void prepareReport(final int action) {
        setReportButtonsEnabled(false);
        status.setText("Preparing diagnostic report…");
        Thread worker = new Thread(() -> {
            try {
                File directory = new File(getFilesDir(), "reports");
                if (!directory.isDirectory() && !directory.mkdirs())
                    throw new java.io.IOException("Cannot create report directory");
                File file = File.createTempFile("S3CE-diagnostic-", ".txt", directory);
                Files.write(file.toPath(), report().getBytes(StandardCharsets.UTF_8));
                runOnUiThread(() -> {
                    setReportButtonsEnabled(true);
                    pendingReport = file.getName();
                    try { presentReport(file, action); }
                    catch (Exception error) { status.setText("Report is ready. Export failed: " + error); }
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    setReportButtonsEnabled(true);
                    status.setText("Cannot prepare report: " + error);
                });
            }
        }, "S3CE-Report");
        worker.setDaemon(true);
        worker.start();
    }

    private void presentReport(File file, int action) throws Exception {
        status.setText("Report ready: " + file.getName());
        if (action == 0) {
            Intent save = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            save.addCategory(Intent.CATEGORY_OPENABLE);
            save.setType("text/plain");
            save.putExtra(Intent.EXTRA_TITLE, file.getName());
            startActivityForResult(save, SAVE_REPORT);
        } else if (action == 1) {
            Uri uri = ReportProvider.uri(file);
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("text/plain");
            send.putExtra(Intent.EXTRA_SUBJECT, "S3CE compatibility diagnostics");
            send.putExtra(Intent.EXTRA_STREAM, uri);
            send.setClipData(ClipData.newRawUri(file.getName(), uri));
            send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(Intent.createChooser(send, "Share S3CE report file"));
        } else {
            final String details = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
            TextView content = new TextView(this);
            content.setText(details);
            content.setTextSize(12);
            content.setTextIsSelectable(true);
            ScrollView scrolling = new ScrollView(this);
            scrolling.addView(content);
            new AlertDialog.Builder(this).setTitle("S3CE diagnostic report").setView(scrolling)
                    .setPositiveButton("Copy", (dialog, which) -> {
                        String copied = details.length() > 65536 ? details.substring(0, 65536) : details;
                        ((ClipboardManager) getSystemService(CLIPBOARD_SERVICE))
                                .setPrimaryClip(ClipData.newPlainText("S3CE diagnostics", copied));
                        status.setText(details.length() > 65536 ? "Copied first 64 KB; Save report keeps the full file."
                                : "Diagnostic report copied.");
                    }).setNegativeButton("Close", null).show();
        }
    }

    @Override protected void onSaveInstanceState(Bundle state) {
        state.putString("pending_report", pendingReport);
        super.onSaveInstanceState(state);
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request != SAVE_REPORT || result != RESULT_OK || data == null || data.getData() == null) return;
        final Uri destination = data.getData();
        final String name = pendingReport;
        if (name == null) { status.setText("Prepare a report again before saving."); return; }
        setReportButtonsEnabled(false);
        Thread save = new Thread(() -> {
            try {
                try (OutputStream output = getContentResolver().openOutputStream(destination, "wt")) {
                    if (output == null) throw new java.io.IOException("The selected destination did not open");
                    Files.copy(ReportProvider.file(getFilesDir(), name).toPath(), output);
                    output.flush();
                }
                runOnUiThread(() -> {
                    setReportButtonsEnabled(true);
                    status.setText("Report saved successfully. Attach that .txt file here.");
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    setReportButtonsEnabled(true);
                    status.setText("Save failed: " + error + "\nTry Share report file or View / copy report.");
                });
            }
        }, "S3CE-SaveReport");
        save.setDaemon(true);
        save.start();
    }

    private void setReportButtonsEnabled(boolean enabled) {
        for (Button button : reportButtons) button.setEnabled(enabled);
    }

    private String report() {
        StringBuilder text = new StringBuilder("S3CE 0.1.3 diagnostic report\n");
        text.append("Android: ").append(Build.VERSION.RELEASE).append(" API ")
                .append(Build.VERSION.SDK_INT).append("\nDevice: ")
                .append(Build.MANUFACTURER).append(' ').append(Build.MODEL)
                .append("\nABIs: ").append(Arrays.toString(Build.SUPPORTED_ABIS))
                .append("\nProcess64: ").append(Process.is64Bit()).append('\n');
        text.append("Launcher selected original rendering: ")
                .append(getPreferences(MODE_PRIVATE).getBoolean("original_rendering", false)).append('\n');
        ExitReport.append(this, text);
        for (String name : new String[]{"compat-java-crash.log", "compat-boot.log", "compat-native.log", "compat-events.log", "compat-java-launcher.log"}) {
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
        if (text.length() > 256 * 1024)
            return text.substring(0, 256 * 1024) + "\n[Report truncated at 256 KB]\n";
        return text.toString();
    }
}
