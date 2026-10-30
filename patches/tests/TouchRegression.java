package com.ideaworks3d.airplay;
import android.view.MotionEvent;
import java.util.Arrays;

public final class TouchRegression {
    private static void send(AirplayView view, int action, int index,
                             int[] ids, float[] xs, float[] ys) {
        if (!MultiTouch.onTouchEvent(view, new MotionEvent(action, index, ids, xs, ys)))
            throw new AssertionError("Event unexpectedly unhandled");
    }
    private static void check(AirplayView view, String... expected) {
        if (!view.events.equals(Arrays.asList(expected)))
            throw new AssertionError("Expected " + Arrays.toString(expected) + " got " + view.events);
    }
    public static void main(String[] args) {
        AirplayView swipe = new AirplayView();
        send(swipe, 0, 0, new int[]{0}, new float[]{10.8f}, new float[]{20.7f});
        send(swipe, 2, 0, new int[]{0}, new float[]{30.1f}, new float[]{22.9f});
        send(swipe, 2, 0, new int[]{0}, new float[]{90.5f}, new float[]{24.1f});
        send(swipe, 1, 0, new int[]{0}, new float[]{100.8f}, new float[]{25.9f});
        check(swipe, "0:4:10:20", "0:6:30:22", "0:6:90:24", "0:5:100:25");

        AirplayView two = new AirplayView();
        send(two, 0, 0, new int[]{0}, new float[]{1}, new float[]{2});
        send(two, 5, 1, new int[]{0,7}, new float[]{1,30}, new float[]{2,40});
        send(two, 2, 0, new int[]{0,7}, new float[]{5,35}, new float[]{6,45});
        send(two, 6, 0, new int[]{0,7}, new float[]{5,35}, new float[]{6,45});
        send(two, 2, 0, new int[]{7}, new float[]{39}, new float[]{49});
        send(two, 1, 0, new int[]{7}, new float[]{40}, new float[]{50});
        check(two, "0:4:1:2", "7:4:30:40", "0:6:5:6", "7:6:35:45",
                   "0:5:5:6", "7:6:39:49", "7:5:40:50");

        AirplayView cancel = new AirplayView();
        send(cancel, 3, 0, new int[]{3,11}, new float[]{9,19}, new float[]{8,18});
        check(cancel, "3:5:9:8", "11:5:19:18");
        System.out.println("PASS: actual APK MultiTouch preserves swipe down/move/up, sparse IDs, pointer removal, and cancel releases.");
    }
}
