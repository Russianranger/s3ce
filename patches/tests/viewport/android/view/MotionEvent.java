package android.view;

/** Immutable coordinates apart from the framework's action/offset contract. */
public final class MotionEvent {
    public static final int ACTION_DOWN=0,ACTION_UP=1,ACTION_MOVE=2,ACTION_CANCEL=3,
        ACTION_POINTER_DOWN=5,ACTION_POINTER_UP=6;
    private int action;
    private final int[] ids;
    private final float[] x,y;
    private final float[][] hx,hy;
    private boolean recycled;
    public MotionEvent(int a,int[] identifiers,float[] xs,float[] ys,float[][] historyX,float[][] historyY){
        action=a;ids=identifiers.clone();x=xs.clone();y=ys.clone();hx=copy(historyX);hy=copy(historyY);
        if(ids.length!=x.length || x.length!=y.length || hx.length!=hy.length)
            throw new IllegalArgumentException("pointer shape");
        for(int i=0;i<hx.length;i++)if(hx[i].length!=x.length || hy[i].length!=y.length)
            throw new IllegalArgumentException("historical pointer shape");
    }
    private static float[][] copy(float[][] a){float[][] r=new float[a.length][];for(int i=0;i<a.length;i++)r[i]=a[i].clone();return r;}
    public static MotionEvent obtain(MotionEvent e){return new MotionEvent(e.action,e.ids,e.x,e.y,e.hx,e.hy);}
    public static MotionEvent obtainNoHistory(MotionEvent e){return new MotionEvent(e.action,e.ids,e.x,e.y,new float[0][],new float[0][]);}
    public int getAction(){return action;}
    public int getActionMasked(){return action&255;}
    public int getActionIndex(){return (action>>8)&255;}
    public void setAction(int value){if(recycled)throw new IllegalStateException("recycled event");action=value;}
    public int getPointerCount(){return ids.length;}
    public int getPointerId(int i){return ids[i];}
    public float getX(int i){return x[i];}
    public float getY(int i){return y[i];}
    public int getHistorySize(){return hx.length;}
    public float getHistoricalX(int pointer,int history){return hx[history][pointer];}
    public float getHistoricalY(int pointer,int history){return hy[history][pointer];}
    public void offsetLocation(float dx,float dy){
        for(int i=0;i<x.length;i++){x[i]+=dx;y[i]+=dy;}
        for(int h=0;h<hx.length;h++)for(int i=0;i<x.length;i++){hx[h][i]+=dx;hy[h][i]+=dy;}
    }
    public void recycle(){if(recycled)throw new IllegalStateException("double recycle");recycled=true;}
}
