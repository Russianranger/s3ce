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
import java.util.Collections;
import java.util.Set;
import java.util.WeakHashMap;

/** Native startup runs in the game's process, independently of reports. */
public final class GameBootActivity extends Activity {
    public static final String EXTRA_GRAPHICS_COMPATIBILITY = "graphics_compatibility";
    private static final RuntimeBootstrap runtime = new RuntimeBootstrap();
    // Per-Activity admission prevents onStart after a failed restored entry,
    // including a mode conflict while another Activity's runtime remains ready.
    private static final Set<Activity> prepared = Collections.newSetFromMap(
            new WeakHashMap<Activity, Boolean>());
    private static native int nativeBootstrap(AssetManager assets, String filesDirectory);
    private static native boolean nativeConfigureGraphics(boolean enabled);

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        String run = "Game startup pid=" + Process.myPid() + " time=" + System.currentTimeMillis() + "\n";
        try {
            boolean graphics = selectedGraphics(this);
            ensureRuntime(this, graphics, run);
            Intent game = new Intent();
            game.setClassName(this, "com.ideaworks3d.thesims3.Main");
            game.putExtra(EXTRA_GRAPHICS_COMPATIBILITY, graphics);
            game.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            GameSession.memory(this, "before-Main-Activity");
            GameSession.phase("Main startActivity ENTER");
            startActivity(game);
            GameSession.phase("Main startActivity RETURN (engine entry not yet established)");
            finish();
        } catch (Throwable error) {
            showFailure(this, run, error);
        }
    }

    /** Called before the original Activity creates an AirplayView or thread. */
    public static synchronized boolean prepareMain(Activity activity) {
        prepared.remove(activity);
        String run = "Main entry pid=" + Process.myPid() + " time=" + System.currentTimeMillis() + "\n";
        try {
            boolean graphics = selectedGraphics(activity);
            if (!runtime.isReady()) GameSession.phase("Main entry requires native bootstrap (process restoration)");
            ensureRuntime(activity, graphics, run);
            Intent intent = activity.getIntent();
            if (intent != null) intent.putExtra(EXTRA_GRAPHICS_COMPATIBILITY, graphics);
            prepared.add(activity);
            return true;
        } catch (Throwable error) {
            showFailure(activity, run, error);
            return false;
        }
    }

    /** An unsuccessful onCreate must never reach the original initNative path. */
    public static synchronized boolean canStartMain(Activity activity) {
        return runtime.isReady() && prepared.contains(activity);
    }

    private static boolean selectedGraphics(Activity activity) {
        Intent intent = activity.getIntent();
        if (intent != null && intent.hasExtra(EXTRA_GRAPHICS_COMPATIBILITY))
            return intent.getBooleanExtra(EXTRA_GRAPHICS_COMPATIBILITY, true);
        // 0.1.14 Main intents did not carry the mode through process restoration.
        return CompatActivity.graphicsCompatibilitySelected(activity);
    }

    private static void ensureRuntime(Activity activity, boolean graphics, String run) throws Throwable {
        runtime.ensure(graphics, () -> {
            writeBootLog(activity, run + "Initializing\n");
            if (Process.is64Bit()) throw new UnsupportedOperationException(
                    "This build requires 32-bit ARM app support.");
            GameSession.memory(activity, "before-loadLibrary");
            GameSession.phase("System.loadLibrary airplay ENTER");
            System.loadLibrary("airplay");
            GameSession.phase("System.loadLibrary airplay RETURN");
            GameSession.phase("nativeConfigureGraphics ENTER compatibility=" + graphics);
            if (!nativeConfigureGraphics(graphics)) throw new IllegalStateException(
                    "Fully close the game before changing rendering mode, then retry.");
            GameSession.phase("nativeConfigureGraphics RETURN success");
            writeBootLog(activity, run + "Graphics compatibility=" + graphics + "\n");
            GameSession.memory(activity, "before-nativeBootstrap");
            GameSession.phase("nativeBootstrap ENTER");
            int version = nativeBootstrap(activity.getAssets(), activity.getFilesDir().getAbsolutePath());
            GameSession.phase("nativeBootstrap RETURN version=" + version);
            if (version < 0) throw new UnsatisfiedLinkError("The legacy runtime could not initialize.");
            GameSession.phase("AirplayActivity class initialization ENTER");
            Class.forName("com.ideaworks3d.airplay.AirplayActivity", true, activity.getClassLoader());
            GameSession.phase("AirplayActivity class initialization RETURN");
            writeBootLog(activity, run + "Native runtime initialized successfully\n");
        });
    }

    private static void showFailure(Activity activity, String run, Throwable error) {
        StringWriter trace = new StringWriter();
        error.printStackTrace(new PrintWriter(trace));
        writeBootLog(activity, run + trace.toString());
        LinearLayout layout = new LinearLayout(activity);
        layout.setOrientation(LinearLayout.VERTICAL);
        TextView message = new TextView(activity);
        message.setText("The Sims 3 CE could not start.\n\n" + error);
        layout.addView(message);
        Button report = new Button(activity);
        report.setText("Open diagnostics");
        report.setOnClickListener(v -> GameDiagnostics.openReports(activity));
        layout.addView(report);
        activity.setContentView(layout);
    }

    private static void writeBootLog(Activity activity, String message) {
        GameSession.phase("Boot " + message);
        File log = new File(activity.getFilesDir(), "compat-boot.log");
        try (FileOutputStream output = new FileOutputStream(log, log.length() < 32768)) {
            output.write(message.getBytes(StandardCharsets.UTF_8));
            output.getFD().sync();
        } catch (Exception ignored) { }
    }
}
