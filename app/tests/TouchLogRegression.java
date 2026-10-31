package com.ideaworks3d.thesims3;

import android.view.MotionEvent;
import java.lang.reflect.Field;
import java.util.concurrent.atomic.AtomicLong;

/** Checks that UI arrival, text gate, and per-action counts remain distinct. */
public final class TouchLogRegression {
    private static long count(String field) throws Exception {
        Field value = GameDiagnostics.class.getDeclaredField(field);
        value.setAccessible(true);
        return ((AtomicLong) value.get(null)).get();
    }
    public static void main(String[] args) throws Exception {
        GameDiagnostics.touch(new MotionEvent(MotionEvent.ACTION_DOWN), false);
        GameDiagnostics.touch(new MotionEvent(MotionEvent.ACTION_MOVE), false);
        GameDiagnostics.touch(new MotionEvent(MotionEvent.ACTION_MOVE), false);
        GameDiagnostics.touch(new MotionEvent(MotionEvent.ACTION_UP), false);
        GameDiagnostics.touch(new MotionEvent(MotionEvent.ACTION_DOWN), true);
        GameDiagnostics.touch(new MotionEvent(MotionEvent.ACTION_MOVE), true);
        GameDiagnostics.touch(new MotionEvent(MotionEvent.ACTION_UP), true);
        GameDiagnostics.touch(new MotionEvent(MotionEvent.ACTION_CANCEL), true);
        if (count("touches") != 8 || count("touchDowns") != 2 || count("touchMoves") != 3
                || count("touchUps") != 2 || count("touchCancels") != 1 || count("touchBlocked") != 3)
            throw new AssertionError("Incorrect action/gate counters");
        Field last = GameDiagnostics.class.getDeclaredField("lastTouch");
        last.setAccessible(true);
        String text = (String) last.get(null);
        for (String expected : new String[]{"action=3", "id=7 x=1300 y=580",
                "source=0x1002", "inputText=true", "blocked=false"})
            if (!text.contains(expected)) throw new AssertionError("Missing " + expected + ": " + text);
        System.out.println("PASS input breadcrumbs distinguish DOWN/MOVE/UP/CANCEL and text gate; CANCEL stays deliverable");
    }
}
