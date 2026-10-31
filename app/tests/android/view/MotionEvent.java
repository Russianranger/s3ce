package android.view;

/** Host-only event values for the input breadcrumb regression. */
public final class MotionEvent {
    public static final int ACTION_DOWN = 0, ACTION_UP = 1, ACTION_MOVE = 2,
            ACTION_CANCEL = 3, ACTION_POINTER_DOWN = 5, ACTION_POINTER_UP = 6;
    private final int action;
    public MotionEvent(int action) { this.action = action; }
    public int getActionMasked() { return action; }
    public int getPointerCount() { return 1; }
    public int getSource() { return 0x1002; }
    public int getPointerId(int index) { if (index != 0) throw new AssertionError(); return 7; }
    public float getX(int index) { if (index != 0) throw new AssertionError(); return 1300; }
    public float getY(int index) { if (index != 0) throw new AssertionError(); return 580; }
}
