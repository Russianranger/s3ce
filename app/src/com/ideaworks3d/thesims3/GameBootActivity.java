package com.ideaworks3d.thesims3;

import android.app.Activity;
import android.content.Intent;
import android.content.res.AssetManager;
import android.os.Bundle;
import android.os.Process;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.File;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/** Native startup runs in the game's process, independently of reports. */
public final class GameBootActivity extends Activity {
    private static native int nativeBootstrap(AssetManager assets, String filesDirectory);

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        String run = "Game startup pid=" + Process.myPid() + " time=" + System.currentTimeMillis() + "\n";
        writeBootLog(run + "Initializing\n");
        try {
            if (Process.is64Bit()) throw new UnsupportedOperationException(
                    "This build requires 32-bit ARM app support.");
            System.loadLibrary("airplay");
            int version = nativeBootstrap(getAssets(), getFilesDir().getAbsolutePath());
            if (version < 0) throw new UnsatisfiedLinkError("The legacy runtime could not initialize.");
            Class.forName("com.ideaworks3d.airplay.AirplayActivity", true, getClassLoader());
            writeBootLog(run + "Native runtime initialized successfully\n");
            Intent game = new Intent();
            game.setClassName(this, "com.ideaworks3d.thesims3.Main");
            game.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            startActivity(game);
            finish();
        } catch (Throwable error) {
            StringWriter trace = new StringWriter();
            error.printStackTrace(new PrintWriter(trace));
            writeBootLog(run + trace.toString());
            LinearLayout layout = new LinearLayout(this);
            layout.setOrientation(LinearLayout.VERTICAL);
            TextView message = new TextView(this);
            message.setText("The Sims 3 CE could not start.\n\n" + error);
            layout.addView(message);
            Button report = new Button(this);
            report.setText("Open diagnostics");
            report.setOnClickListener(v -> GameDiagnostics.openReports(this));
            layout.addView(report);
            setContentView(layout);
        }
    }

    private void writeBootLog(String message) {
        try {
            Files.write(new File(getFilesDir(), "compat-boot.log").toPath(),
                    message.getBytes(StandardCharsets.UTF_8));
        } catch (Exception ignored) { }
    }
}
