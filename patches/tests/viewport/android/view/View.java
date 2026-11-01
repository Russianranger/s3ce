package android.view;
import android.app.Activity;
public class View {
    public static final int VISIBLE=0,INVISIBLE=4,GONE=8;
    public static int insetReads;
    protected final Activity activity;
    protected ViewGroup parent;
    protected int left,top,right,bottom,measuredWidth,measuredHeight;
    public int background;
    private Object rootInsets;
    public View(Activity value){activity=value;}
    public final void measure(int widthSpec,int heightSpec){onMeasure(widthSpec,heightSpec);}
    protected void onMeasure(int widthSpec,int heightSpec){setMeasuredDimension(MeasureSpec.getSize(widthSpec),MeasureSpec.getSize(heightSpec));}
    protected final void setMeasuredDimension(int width,int height){measuredWidth=width;measuredHeight=height;}
    public int getMeasuredWidth(){return measuredWidth;}
    public int getMeasuredHeight(){return measuredHeight;}
    public void layout(int l,int t,int r,int b){boolean change=l!=left||t!=top||r!=right||b!=bottom;left=l;top=t;right=r;bottom=b;onLayout(change,l,t,r,b);}
    protected void onLayout(boolean changed,int l,int t,int r,int b){}
    public int getWidth(){return right-left;}
    public int getHeight(){return bottom-top;}
    public int getLeft(){return left;}
    public int getTop(){return top;}
    public int getRight(){return right;}
    public int getBottom(){return bottom;}
    public void getLocationOnScreen(int[] out){out[0]=left;out[1]=top;if(parent!=null){int[] p=new int[2];parent.getLocationOnScreen(p);out[0]+=p[0];out[1]+=p[1];}}
    public void setBackgroundColor(int color){background=color;}
    public boolean dispatchTouchEvent(MotionEvent event){return onTouchEvent(event);}
    public boolean onTouchEvent(MotionEvent event){return false;}
    public void onWindowFocusChanged(boolean value){}
    protected void onWindowVisibilityChanged(int value){}
    protected void onDetachedFromWindow(){}
    public void testVisibility(int value){onWindowVisibilityChanged(value);}
    public void testDetach(){onDetachedFromWindow();}
    public void testSetRootInsets(Object value){rootInsets=value;}
    public Object getRootWindowInsets(){insetReads++;return rootInsets;}
    public static final class MeasureSpec {
        public static final int EXACTLY=0x40000000;
        public static int getSize(int spec){return spec&0x3fffffff;}
        public static int makeMeasureSpec(int size,int mode){return size|mode;}
    }
}
