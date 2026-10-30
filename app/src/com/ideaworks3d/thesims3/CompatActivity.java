package com.ideaworks3d.thesims3;

import android.app.Activity;
import android.content.Intent;
import android.content.res.AssetManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Process;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.File;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;

/** Starts the preserved engine only after an observable compatibility check. */
public final class CompatActivity extends Activity {
    private String lastError = "";
    private TextView status;
    private static native int nativeBootstrap(AssetManager assets, String filesDirectory);

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
        status.setText("The Sims 3 CE\nExperimental Android compatibility build 0.1.0\n\n"
                + "Touch controls. Saves stay on this device.\n");
        layout.addView(status);
        Button play = new Button(this);
        play.setText("Start game");
        play.setOnClickListener(v -> startGame());
        layout.addView(play);
        Button diagnostics = new Button(this);
        diagnostics.setText("Share diagnostics");
        diagnostics.setOnClickListener(v -> {
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("text/plain");
            send.putExtra(Intent.EXTRA_SUBJECT, "S3CE compatibility diagnostics");
            send.putExtra(Intent.EXTRA_TEXT, report());
            startActivity(Intent.createChooser(send, "Share S3CE diagnostics"));
        });
        layout.addView(diagnostics);
        setContentView(layout);
        if (state == null) startGame();
    }

    private void startGame() {
        try {
            if (Process.is64Bit()) throw new UnsupportedOperationException(
                    "This preservation build requires a device with 32-bit ARM app support.");
            System.loadLibrary("airplay");
            int version = nativeBootstrap(getAssets(), getFilesDir().getAbsolutePath());
            if (version < 0) throw new UnsatisfiedLinkError(
                    "The legacy runtime could not initialize. Share diagnostics for the loader details.");
            // Loading here lets Java loader errors reach the diagnostic screen.
            Class.forName("com.ideaworks3d.airplay.AirplayActivity", true, getClassLoader());
            Intent game = new Intent();
            game.setClassName(this, "com.ideaworks3d.thesims3.Main");
            startActivity(game);
        } catch (Throwable error) {
            StringWriter trace = new StringWriter();
            error.printStackTrace(new PrintWriter(trace));
            lastError = trace.toString();
            status.setText("The Sims 3 CE could not start.\n\n" + error.toString()
                    + "\n\nUse Share diagnostics to send the details.");
        }
    }

    private String report() {
        StringBuilder text = new StringBuilder("S3CE 0.1.0 experimental\n");
        text.append("Android: ").append(Build.VERSION.RELEASE).append(" API ")
                .append(Build.VERSION.SDK_INT).append("\nDevice: ")
                .append(Build.MANUFACTURER).append(' ').append(Build.MODEL)
                .append("\nABIs: ").append(Arrays.toString(Build.SUPPORTED_ABIS))
                .append("\nProcess64: ").append(Process.is64Bit()).append('\n');
        text.append(lastError);
        File nativeLog = new File(getFilesDir(), "compat-native.log");
        try {
            if (nativeLog.isFile() && nativeLog.length() <= 131072)
                text.append("\nNative loader:\n").append(new String(
                        Files.readAllBytes(nativeLog.toPath()), StandardCharsets.UTF_8));
        } catch (Exception error) { text.append("\nCannot read loader log: ").append(error); }
        return text.toString();
    }
}
