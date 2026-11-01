package com.ideaworks3d.thesims3;

import android.app.Activity;
import android.graphics.Color;
import android.os.Build;
import android.util.Log;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;

/** Owns a real, unstretched16:9 child surface and inert surrounding margins.
 * Android's window decor fits system bars/cutouts once. This container fits its
 * actual measured content, without subtracting root-window insets a second time.
 * Normal events use ViewGroup's child-local dispatch without another offset.
 * CANCEL's separate framework fast path is normalized at its owning boundary.
 * No input rescaling is applied to the original Airplay touch bridge.
 */
public final class GameViewport extends ViewGroup {
    private static final AtomicInteger layoutLogs = new AtomicInteger();
    private final View game;
    private final File eventLog;
    private Bounds bounds = fit(0, 0);
    private MotionEvent lastEvent;
    private boolean forwarding;
    private boolean blocked;
    private String lastGeometry;
    private boolean laidOut;
    private int lastOriginX, lastOriginY;

    /** No original game classes or JNI are referenced; usable by platform probes. */
    public static void install(Activity activity, View game) {
        if (activity == null || game == null) throw new IllegalArgumentException("Missing viewport owner/view");
        Window window = activity.getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
        window.setStatusBarColor(Color.BLACK);
        window.setNavigationBarColor(Color.BLACK);
        if (Build.VERSION.SDK_INT >= 30) window.setDecorFitsSystemWindows(true);
        if (Build.VERSION.SDK_INT >= 28) {
            WindowManager.LayoutParams attributes = window.getAttributes();
            attributes.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_NEVER;
            window.setAttributes(attributes);
        }
        window.setBackgroundDrawableResource(android.R.color.black);
        activity.setContentView(new GameViewport(activity, game));
    }

    private GameViewport(Activity activity, View child) {
        super(activity);
        game = child;
        eventLog = new File(activity.getFilesDir(), "compat-events.log");
        setBackgroundColor(Color.BLACK);
        // One original MultiTouch bridge owns all IDs in the gesture.
        setMotionEventSplittingEnabled(false);
        addView(child, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT));
    }

    /** Largest exact integer16:9 rectangle in already fitted content pixels. */
    public static Bounds fit(int width, int height) {
        width = Math.max(0, width);
        height = Math.max(0, height);
        int unit = Math.min(width / 16, height / 9);
        int childWidth = unit * 16;
        int childHeight = unit * 9;
        return new Bounds((width - childWidth) / 2, (height - childHeight) / 2,
                          childWidth, childHeight);
    }

    public static final class Bounds {
        public final int left, top, width, height;
        Bounds(int left, int top, int width, int height) {
            this.left = left; this.top = top; this.width = width; this.height = height;
        }
        boolean contains(float x, float y) {
            return width > 0 && height > 0 && x >= left && y >= top
                    && x < left + width && y < top + height;
        }
        boolean same(Bounds other) {
            return left == other.left && top == other.top && width == other.width && height == other.height;
        }
    }

    @Override protected void onMeasure(int widthSpec, int heightSpec) {
        // Activity content is MATCH_PARENT. Window decor already owns safe insets.
        int width = MeasureSpec.getSize(widthSpec), height = MeasureSpec.getSize(heightSpec);
        Bounds next = fit(width, height);
        game.measure(MeasureSpec.makeMeasureSpec(next.width, MeasureSpec.EXACTLY),
                     MeasureSpec.makeMeasureSpec(next.height, MeasureSpec.EXACTLY));
        setMeasuredDimension(width, height);
    }

    @Override protected void onLayout(boolean changed, int left, int top, int right, int bottom) {
        Bounds next = fit(right - left, bottom - top);
        int[] origin = new int[2];
        getLocationOnScreen(origin);
        if (!bounds.same(next) || !laidOut || origin[0] != lastOriginX || origin[1] != lastOriginY)
            cancelGesture();
        lastOriginX = origin[0]; lastOriginY = origin[1]; laidOut = true;
        bounds = next;
        game.layout(next.left, next.top, next.left + next.width, next.top + next.height);
        recordGeometry();
    }

    private boolean allInside(MotionEvent event) {
        for (int i = 0; i < event.getPointerCount(); ++i) {
            if (!bounds.contains(event.getX(i), event.getY(i))) return false;
            // Batched MOVE history can reveal a margin exit followed by reentry
            // before the UI thread dispatches the current sample.
            for (int h = 0; h < event.getHistorySize(); ++h)
                if (!bounds.contains(event.getHistoricalX(i, h), event.getHistoricalY(i, h))) return false;
        }
        return event.getPointerCount() > 0;
    }

    @Override public boolean dispatchTouchEvent(MotionEvent event) {
        int action = event.getActionMasked();
        if (action == MotionEvent.ACTION_DOWN) {
            cancelGesture();
            blocked = false;
        }
        // ViewGroup's CANCEL fast path deliberately skips normal child offsets.
        // Retire this container's owned active snapshot at that boundary.
        if (action == MotionEvent.ACTION_CANCEL) {
            cancelGesture();
            blocked = false;
            return true;
        }
        if (blocked) {
            if (action == MotionEvent.ACTION_UP) blocked = false;
            return true;
        }
        if (!allInside(event)) {
            cancelGesture();
            blocked = action != MotionEvent.ACTION_UP && action != MotionEvent.ACTION_CANCEL;
            return true;
        }
        // A pointer born in a margin cannot acquire the child by moving inside.
        if (!forwarding && action != MotionEvent.ACTION_DOWN) return true;
        forwarding = true;
        rememberActivePointers(event);
        super.dispatchTouchEvent(event);
        if (action == MotionEvent.ACTION_UP) finishGesture();
        return true;
    }

    /** Retain post-event ownership, excluding the finger a POINTER_UP retires.
     * Legacy MultiTouch turns every CANCEL pointer into native UP; retaining
     * the just-ended finger would release it twice.
     */
    private void rememberActivePointers(MotionEvent event) {
        MotionEvent next;
        int count = event.getPointerCount();
        int ended = event.getActionIndex();
        if (event.getActionMasked() == MotionEvent.ACTION_POINTER_UP && count > 1 && ended < count) {
            MotionEvent.PointerProperties[] properties = new MotionEvent.PointerProperties[count - 1];
            MotionEvent.PointerCoords[] coordinates = new MotionEvent.PointerCoords[count - 1];
            // Public obtain has no raw-offset argument. Seed screen coordinates,
            // then restore parent-local positions; offsetLocation retains raw X/Y.
            float rawOffsetX = event.getRawX() - event.getX(0);
            float rawOffsetY = event.getRawY() - event.getY(0);
            int out = 0;
            for (int i = 0; i < count; ++i) if (i != ended) {
                properties[out] = new MotionEvent.PointerProperties();
                coordinates[out] = new MotionEvent.PointerCoords();
                event.getPointerProperties(i, properties[out]);
                event.getPointerCoords(i, coordinates[out]);
                coordinates[out].x += rawOffsetX;
                coordinates[out].y += rawOffsetY;
                ++out;
            }
            next = MotionEvent.obtain(event.getDownTime(), event.getEventTime(), MotionEvent.ACTION_MOVE,
                    count - 1, properties, coordinates, event.getMetaState(), event.getButtonState(),
                    event.getXPrecision(), event.getYPrecision(), event.getDeviceId(), event.getEdgeFlags(),
                    event.getSource(), event.getFlags());
            next.offsetLocation(-rawOffsetX, -rawOffsetY);
        } else next = MotionEvent.obtainNoHistory(event);
        if (lastEvent != null) lastEvent.recycle();
        lastEvent = next;
    }

    private void finishGesture() {
        forwarding = false;
        if (lastEvent != null) lastEvent.recycle();
        lastEvent = null;
    }

    private void cancelGesture() {
        if (!forwarding) return;
        forwarding = false;
        blocked = true;
        MotionEvent previous = lastEvent;
        lastEvent = null;
        if (previous == null) return;
        try {
            previous.setAction(MotionEvent.ACTION_CANCEL);
            // Android's CANCEL fast path does not offset coordinates. Convert
            // this owned copy once while the old child bounds are installed.
            // Super still retires its touch-target bookkeeping.
            previous.offsetLocation(-game.getLeft(), -game.getTop());
            super.dispatchTouchEvent(previous);
        } finally {
            previous.recycle();
        }
    }

    @Override public void onWindowFocusChanged(boolean hasFocus) {
        if (!hasFocus) cancelGesture();
        super.onWindowFocusChanged(hasFocus);
    }
    @Override protected void onWindowVisibilityChanged(int visibility) {
        if (visibility != View.VISIBLE) cancelGesture();
        super.onWindowVisibilityChanged(visibility);
    }
    @Override protected void onDetachedFromWindow() {
        cancelGesture();
        super.onDetachedFromWindow();
    }

    private void recordGeometry() {
        int[] child = new int[2], parent = new int[2];
        game.getLocationOnScreen(child);
        getLocationOnScreen(parent);
        String line = "VIEWPORT child=" + game.getClass().getName()
                + " bounds=[" + child[0] + "," + child[1] + "][" + (child[0] + game.getWidth())
                + "," + (child[1] + game.getHeight()) + "] parent=[" + parent[0] + "," + parent[1]
                + "][" + (parent[0] + getWidth()) + "," + (parent[1] + getHeight()) + "]";
        if (line.equals(lastGeometry)) return;
        lastGeometry = line;
        if (layoutLogs.getAndIncrement() >= 32) return;
        Log.i("S3CEViewport", line);
        try (FileOutputStream stream = new FileOutputStream(eventLog, true)) {
            stream.write(("time=" + System.currentTimeMillis() + " pid=" + android.os.Process.myPid()
                    + " " + line + "\n").getBytes(StandardCharsets.UTF_8));
        } catch (Exception error) { Log.w("S3CEViewport", "Could not persist viewport geometry", error); }
    }
}
