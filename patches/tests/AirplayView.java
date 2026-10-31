package com.ideaworks3d.airplay;
import java.util.ArrayList;
import java.util.List;

/** Native-call capture; the actual MultiTouch code comes from the tested APK. */
public final class AirplayView {
    public boolean m_InputTextRunning;
    public final List<String> events = new ArrayList<>();
    public void onMotionEvent(int id, int action, int x, int y) {
        events.add(id + ":" + action + ":" + x + ":" + y);
    }
}
