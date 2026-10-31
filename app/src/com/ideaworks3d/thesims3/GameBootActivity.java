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
import java.io.FileOutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;

/** Native startup runs in the game's process, independently of reports. */
public final class GameBootActivity extends Activity {
    private static native int nativeBootstrap(AssetManager assets, String filesDirectory);
    private static native boolean nativeConfigureGraphics(boolean enabled);

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        String run = "Game startup pid=" + Process.myPid() + " time=" + System.currentTimeMillis() + "\n";
        writeBootLog(run + "Initializing\n");
        try {
            if (Process.is64Bit()) throw new UnsupportedOperationException(
                    "This build requires 32-bit ARM app support.");
            GameSession.memory(this, "before-loadLibrary");
            GameSession.phase("System.loadLibrary airplay ENTER");
            System.loadLibrary("airplay");
            GameSession.phase("System.loadLibrary airplay RETURN");
            boolean graphics = getIntent().getBooleanExtra("graphics_compatibility", true);
            GameSession.phase("nativeConfigureGraphics ENTER compatibility=" + graphics);
            if (!nativeConfigureGraphics(graphics)) throw new IllegalStateException(
                    "Fully close the game before changing rendering mode, then retry.");
            GameSession.phase("nativeConfigureGraphics RETURN success");
            writeBootLog(run + "Graphics compatibility=" + graphics + "\n");
            GameSession.memory(this, "before-nativeBootstrap");
            GameSession.phase("nativeBootstrap ENTER");
            int version = nativeBootstrap(getAssets(), getFilesDir().getAbsolutePath());
            GameSession.phase("nativeBootstrap RETURN version=" + version);
            if (version < 0) throw new UnsatisfiedLinkError("The legacy runtime could not initialize.");
            GameSession.phase("AirplayActivity class initialization ENTER");
            Class.forName("com.ideaworks3d.airplay.AirplayActivity", true, getClassLoader());
            GameSession.phase("AirplayActivity class initialization RETURN");
            writeBootLog(run + "Native runtime initialized successfully\n");
            Intent game = new Intent();
            game.setClassName(this, "com.ideaworks3d.thesims3.Main");
            game.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            GameSession.memory(this, "before-Main-Activity");
            GameSession.phase("Main startActivity ENTER");
            startActivity(game);
            GameSession.phase("Main startActivity RETURN (engine entry not yet established)");
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
        GameSession.phase("Boot " + message);
        File log = new File(getFilesDir(), "compat-boot.log");
        try (FileOutputStream output = new FileOutputStream(log, log.length() < 32768)) {
            output.write(message.getBytes(StandardCharsets.UTF_8));
            output.getFD().sync();
        } catch (Exception ignored) { }
    }
}
