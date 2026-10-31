package com.ideaworks3d.thesims3;

import android.view.MotionEvent;
import java.util.ArrayList;
import java.util.List;

/** The test deliberately provides only the production two-argument descriptor. */
public final class GameDiagnostics {
    public static final List<MotionEvent> events = new ArrayList<>();
    public static final List<Boolean> gates = new ArrayList<>();
    public static void touch(MotionEvent event, boolean inputTextRunning) {
        events.add(event);
        gates.add(inputTextRunning);
    }
}
