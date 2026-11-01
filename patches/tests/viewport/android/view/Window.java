package android.view;
import android.os.Build;
public final class Window {
    public int flags, statusColor, navigationColor, background, decorCalls, attributeCalls;
    public boolean decorFits;
    private WindowManager.LayoutParams attributes=new WindowManager.LayoutParams();
    public void addFlags(int value) { flags|=value; }
    public void setStatusBarColor(int value) { statusColor=value; }
    public void setNavigationBarColor(int value) { navigationColor=value; }
    public void setBackgroundDrawableResource(int value) { background=value; }
    public void setDecorFitsSystemWindows(boolean value) {
        if(Build.VERSION.SDK_INT<30) throw new NoSuchMethodError("API30 decor fit");
        decorCalls++; decorFits=value;
    }
    public WindowManager.LayoutParams getAttributes() { return attributes; }
    public void setAttributes(WindowManager.LayoutParams value) {
        if(Build.VERSION.SDK_INT<28) throw new NoSuchFieldError("API28 cutout policy");
        attributeCalls++; attributes=value;
    }
}
