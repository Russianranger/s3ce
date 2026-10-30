package android.view;

/** Minimal host double preserving Android's index/ID distinction. */
public final class MotionEvent {
    private final int action;
    private final int[] ids;
    private final float[] xs, ys;
    public MotionEvent(int masked, int index, int[] ids, float[] xs, float[] ys) {
        this.action = masked | (index << 8);
        this.ids = ids;
        this.xs = xs;
        this.ys = ys;
    }
    public int getAction() { return action; }
    public int getActionMasked() { return action & 255; }
    public int getActionIndex() { return (action >>> 8) & 255; }
    public int getPointerCount() { return ids.length; }
    public int getPointerId(int index) { return ids[index]; }
    public float getX(int index) { return xs[index]; }
    public float getY(int index) { return ys[index]; }
}
