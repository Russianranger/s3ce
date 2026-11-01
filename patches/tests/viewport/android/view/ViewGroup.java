package android.view;
import android.app.Activity;
import java.util.ArrayList;
import java.util.List;

/** Bounded normal dispatch: one touch target, all IDs/history translated once. */
public class ViewGroup extends View {
    private final List<View> children=new ArrayList<>();
    private View touchTarget;
    public boolean splitting=true;
    public ViewGroup(Activity owner){super(owner);}
    public void setMotionEventSplittingEnabled(boolean enabled){splitting=enabled;}
    public void addView(View child,LayoutParams params){if(child.parent!=null)throw new IllegalStateException("already parented");children.add(child);child.parent=this;}
    public View getChildAt(int i){return children.get(i);}
    public int getChildCount(){return children.size();}
    @Override public boolean dispatchTouchEvent(MotionEvent event){
        int action=event.getActionMasked();
        if(action==MotionEvent.ACTION_DOWN){
            touchTarget=null;
            for(int i=children.size()-1;i>=0;i--){View c=children.get(i);float x=event.getX(0),y=event.getY(0);
                if(x>=c.left&&y>=c.top&&x<c.right&&y<c.bottom){touchTarget=c;break;}
            }
        }
        View child=touchTarget;
        if(child==null)return onTouchEvent(event);
        MotionEvent local=MotionEvent.obtain(event);
        // Android ViewGroup's dispatchTransformedTouchEvent CANCEL fast path
        // bypasses the usual child translation, as confirmed by the API35 probe.
        if(action!=MotionEvent.ACTION_CANCEL)local.offsetLocation(-child.left,-child.top);
        boolean handled=child.dispatchTouchEvent(local);
        local.recycle();
        if(action==MotionEvent.ACTION_UP||action==MotionEvent.ACTION_CANCEL)touchTarget=null;
        return handled;
    }
    @Override public void testDetach(){super.testDetach();for(View c:children)c.testDetach();touchTarget=null;}
    public static class LayoutParams {
        public static final int MATCH_PARENT=-1;
        public int width,height;
        public LayoutParams(int w,int h){width=w;height=h;}
    }
}
