package io.github.russianranger.s3ce.viewportprobe;

import android.app.Activity;
import android.content.res.Configuration;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.util.DisplayMetrics;
import android.util.AtomicFile;
import android.util.Log;
import android.view.MotionEvent;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.view.WindowInsets;
import dalvik.system.DexClassLoader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.json.JSONArray;
import org.json.JSONObject;

/** Real framework fixture: candidate helper bytes run; the game engine never runs. */
public final class ViewportProbe extends Activity {
    private final JSONArray events = new JSONArray();
    private final Handler handler = new Handler();
    private ProbeSurface child;
    private JSONObject identity;
    private String failure;
    private boolean focused, resumed;
    private int reports;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        try {
            identity = new JSONObject(new String(readAsset("candidate-identity.json"), StandardCharsets.UTF_8));
            byte[] payload = readAsset("candidate-classes2.dex");
            if (!hex(MessageDigest.getInstance("SHA-256").digest(payload)).equals(identity.getString("classes2_sha256")))
                throw new IllegalStateException("Candidate DEX asset digest mismatch");
            File dex = new File(getCodeCacheDir(), "candidate-classes2.dex");
            if (dex.exists() && !dex.delete()) throw new IllegalStateException("Cannot replace probe DEX");
            // Open first, mark read-only, then write through the owned descriptor:
            // this also satisfies Android14+ dynamic-code file requirements.
            try (FileOutputStream out = new FileOutputStream(dex)) {
                if (!dex.setReadOnly()) throw new IllegalStateException("Cannot make probe DEX read-only");
                out.write(payload); out.getFD().sync();
            }
            DexClassLoader loader = new DexClassLoader(dex.getAbsolutePath(),
                    getCodeCacheDir().getAbsolutePath(), null, getClassLoader());
            Class<?> helper = Class.forName("com.ideaworks3d.thesims3.GameViewport", true, loader);
            if (helper.getClassLoader() != loader) throw new IllegalStateException("Helper did not load from candidate DEX");
            identity.put("loaded_helper", helper.getName());
            identity.put("helper_loader", helper.getClassLoader().getClass().getName());
            child = new ProbeSurface();
            helper.getMethod("install", Activity.class, View.class).invoke(null, this, child);
            child.getViewTreeObserver().addOnGlobalLayoutListener(() -> writeReport());
            handler.postDelayed(this::writeReport, 500);
        } catch (Throwable error) {
            failure = Log.getStackTraceString(error);
            Log.e("S3CEPlatformProbe", "Candidate helper probe failed", error);
            writeReport();
        }
    }

    private byte[] readAsset(String name) throws java.io.IOException {
        try (InputStream in = getAssets().open(name);
             java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream()) {
            byte[] buffer = new byte[16384]; int count;
            while ((count = in.read(buffer)) != -1) out.write(buffer, 0, count);
            return out.toByteArray();
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder value = new StringBuilder();
        for (byte b : bytes) value.append(String.format(java.util.Locale.ROOT, "%02x", b & 255));
        return value.toString();
    }

    private static JSONArray bounds(View view) throws org.json.JSONException {
        int[] xy = new int[2]; view.getLocationOnScreen(xy);
        return new JSONArray(new int[] {xy[0], xy[1], xy[0] + view.getWidth(), xy[1] + view.getHeight()});
    }

    private void writeReport() {
        try {
            JSONObject report = new JSONObject();
            report.put("schema", 1);
            report.put("scope", "Actual Android framework + exact candidate viewport helper; SurfaceView input fixture; no game engine or gameplay");
            report.put("api", Build.VERSION.SDK_INT); report.put("identity", identity);
            report.put("target_sdk", getApplicationInfo().targetSdkVersion);
            report.put("requested_orientation", getRequestedOrientation());
            report.put("window_cutout_mode", getWindow().getAttributes().layoutInDisplayCutoutMode);
            report.put("display_rotation", getWindowManager().getDefaultDisplay().getRotation());
            report.put("failure", failure == null ? JSONObject.NULL : failure);
            report.put("window_focused", focused); report.put("resumed", resumed);
            report.put("report_sequence", ++reports);
            DisplayMetrics metrics = new DisplayMetrics();
            getWindowManager().getDefaultDisplay().getRealMetrics(metrics);
            report.put("display_size", new JSONArray(new int[] {metrics.widthPixels, metrics.heightPixels}));
            View decor = getWindow().getDecorView(); report.put("decor_bounds", bounds(decor));
            report.put("hardware_accelerated", decor.isHardwareAccelerated());
            android.view.DisplayCutout globalCutout = getWindowManager().getDefaultDisplay().getCutout();
            if (globalCutout != null) report.put("display_cutout_insets", new JSONArray(new int[] {
                globalCutout.getSafeInsetLeft(), globalCutout.getSafeInsetTop(),
                globalCutout.getSafeInsetRight(), globalCutout.getSafeInsetBottom()}));
            else report.put("display_cutout_insets", JSONObject.NULL);
            WindowInsets insets = decor.getRootWindowInsets();
            if (insets != null) report.put("system_insets", new JSONArray(new int[] {
                insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom()}));
            if (insets != null && Build.VERSION.SDK_INT >= 28 && insets.getDisplayCutout() != null) {
                android.view.DisplayCutout cutout = insets.getDisplayCutout();
                report.put("cutout_insets", new JSONArray(new int[] {cutout.getSafeInsetLeft(), cutout.getSafeInsetTop(),
                    cutout.getSafeInsetRight(), cutout.getSafeInsetBottom()}));
                report.put("cutout_rectangles", cutout.getBoundingRects().toString());
            } else report.put("cutout_insets", JSONObject.NULL);
            if (child != null && child.getParent() instanceof View) {
                report.put("child_bounds", bounds(child));
                report.put("parent_bounds", bounds((View) child.getParent()));
                report.put("parent_class", child.getParent().getClass().getName());
                report.put("child_measured_size", new JSONArray(new int[] {child.getMeasuredWidth(), child.getMeasuredHeight()}));
                report.put("surface_frame", new JSONArray(new int[] {child.getHolder().getSurfaceFrame().width(), child.getHolder().getSurfaceFrame().height()}));
            }
            report.put("touch_events", events);
            byte[] encoded = (report.toString(2) + "\n").getBytes(StandardCharsets.UTF_8);
            AtomicFile target = new AtomicFile(new File(getFilesDir(), "probe.json"));
            FileOutputStream out = target.startWrite();
            try { out.write(encoded); target.finishWrite(out); }
            catch (Throwable error) { target.failWrite(out); throw error; }
        } catch (Throwable error) { Log.e("S3CEPlatformProbe", "Cannot persist probe result", error); }
    }

    @Override protected void onResume() { super.onResume(); resumed = true; writeReport(); }
    @Override protected void onPause() { resumed = false; super.onPause(); writeReport(); }
    @Override public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus); focused = hasFocus; writeReport();
    }
    @Override public void onConfigurationChanged(Configuration config) {
        super.onConfigurationChanged(config); handler.postDelayed(this::writeReport, 250);
    }

    private final class ProbeSurface extends SurfaceView implements SurfaceHolder.Callback {
        ProbeSurface() { super(ViewportProbe.this); getHolder().addCallback(this); setBackgroundColor(Color.rgb(30, 110, 140)); }
        @Override public boolean onTouchEvent(MotionEvent event) {
            try {
                if (events.length() >= 256) throw new IllegalStateException("Probe event bound exceeded");
                JSONObject item = new JSONObject(); item.put("action", event.getActionMasked());
                item.put("x", event.getX()); item.put("y", event.getY());
                item.put("raw_x", event.getRawX()); item.put("raw_y", event.getRawY());
                item.put("pointer_count", event.getPointerCount()); events.put(item); writeReport();
            } catch (Throwable error) { failure = Log.getStackTraceString(error); writeReport(); }
            return true;
        }
        private void drawSurface() {
            Canvas canvas = null;
            try {
                canvas = getHolder().lockCanvas(); if (canvas == null) return;
                canvas.drawColor(Color.rgb(30, 110, 140));
                Paint paint = new Paint(); paint.setColor(Color.WHITE); paint.setTextSize(40);
                canvas.drawText("Actual candidate viewport helper / Android " + Build.VERSION.SDK_INT, 35, 65, paint);
                canvas.drawText("SurfaceView test fixture - native game is not running", 35, 120, paint);
                paint.setColor(Color.YELLOW); paint.setStrokeWidth(8); paint.setStyle(Paint.Style.STROKE);
                canvas.drawRect(4, 4, canvas.getWidth() - 4, canvas.getHeight() - 4, paint);
            } finally { if (canvas != null) getHolder().unlockCanvasAndPost(canvas); }
        }
        @Override public void surfaceCreated(SurfaceHolder holder) { drawSurface(); writeReport(); }
        @Override public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) { drawSurface(); writeReport(); }
        @Override public void surfaceDestroyed(SurfaceHolder holder) { writeReport(); }
    }
}
