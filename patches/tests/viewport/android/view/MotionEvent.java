package android.view;

/** Bounded public MotionEvent coordinate/copy/metadata contract. */
public final class MotionEvent {
    public static final int ACTION_DOWN=0,ACTION_UP=1,ACTION_MOVE=2,ACTION_CANCEL=3,
        ACTION_POINTER_DOWN=5,ACTION_POINTER_UP=6;
    public static final class PointerProperties {
        public int id,toolType;
        public void copyFrom(PointerProperties other){id=other.id;toolType=other.toolType;}
    }
    public static final class PointerCoords {
        public float x,y,pressure,size,touchMajor,touchMinor,toolMajor,toolMinor,orientation;
        public void copyFrom(PointerCoords o){x=o.x;y=o.y;pressure=o.pressure;size=o.size;touchMajor=o.touchMajor;touchMinor=o.touchMinor;toolMajor=o.toolMajor;toolMinor=o.toolMinor;orientation=o.orientation;}
    }
    private int action;
    private final int[] ids;
    private final float[] x,y;
    private final float[][] hx,hy;
    private final PointerProperties[] properties;
    private final PointerCoords[] coordinates;
    private long downTime=123,eventTime=456;
    private int metaState=5,buttonState=6,deviceId=7,edgeFlags=8,source=0x1002,flags=9;
    private float xPrecision=.5f,yPrecision=.75f,rawX,rawY;
    private boolean recycled;
    public MotionEvent(int a,int[] identifiers,float[] xs,float[] ys,float[][] historyX,float[][] historyY){
        for(int id:identifiers)if(id<0||id>31)throw new IllegalArgumentException("Android pointer ID");
        action=a;ids=identifiers.clone();x=xs.clone();y=ys.clone();hx=copy(historyX);hy=copy(historyY);
        if(ids.length!=x.length || x.length!=y.length || hx.length!=hy.length)
            throw new IllegalArgumentException("pointer shape");
        for(int i=0;i<hx.length;i++)if(hx[i].length!=x.length || hy[i].length!=y.length)
            throw new IllegalArgumentException("historical pointer shape");
        properties=new PointerProperties[ids.length];coordinates=new PointerCoords[ids.length];
        for(int i=0;i<ids.length;i++){
            properties[i]=new PointerProperties();properties[i].id=ids[i];properties[i].toolType=i+1;
            coordinates[i]=new PointerCoords();coordinates[i].pressure=.4f+i*.1f;coordinates[i].size=.6f;
            coordinates[i].touchMajor=2+i;coordinates[i].touchMinor=3+i;coordinates[i].toolMajor=4+i;coordinates[i].toolMinor=5+i;coordinates[i].orientation=.2f;
        }
        if(ids.length>0){rawX=x[0];rawY=y[0];}
    }
    private static float[][] copy(float[][] a){float[][] r=new float[a.length][];for(int i=0;i<a.length;i++)r[i]=a[i].clone();return r;}
    private static MotionEvent duplicate(MotionEvent e,boolean history){
        MotionEvent r=new MotionEvent(e.action,e.ids,e.x,e.y,history?e.hx:new float[0][],history?e.hy:new float[0][]);
        for(int i=0;i<e.ids.length;i++){r.properties[i].copyFrom(e.properties[i]);r.coordinates[i].copyFrom(e.coordinates[i]);}
        r.downTime=e.downTime;r.eventTime=e.eventTime;r.metaState=e.metaState;r.buttonState=e.buttonState;
        r.deviceId=e.deviceId;r.edgeFlags=e.edgeFlags;r.source=e.source;r.flags=e.flags;
        r.xPrecision=e.xPrecision;r.yPrecision=e.yPrecision;r.rawX=e.rawX;r.rawY=e.rawY;return r;
    }
    public static MotionEvent obtain(MotionEvent e){return duplicate(e,true);}
    public static MotionEvent obtainNoHistory(MotionEvent e){return duplicate(e,false);}
    public static MotionEvent obtain(long down,long time,int action,int count,PointerProperties[] props,PointerCoords[] coords,
                                    int meta,int buttons,float xp,float yp,int device,int edges,int src,int eventFlags){
        if(count<=0||count>props.length||count>coords.length)throw new IllegalArgumentException("pointer count");
        int[] ids=new int[count];float[] x=new float[count],y=new float[count];
        for(int i=0;i<count;i++){ids[i]=props[i].id;x[i]=coords[i].x;y[i]=coords[i].y;}
        MotionEvent r=new MotionEvent(action,ids,x,y,new float[0][],new float[0][]);
        for(int i=0;i<count;i++){r.properties[i].copyFrom(props[i]);r.coordinates[i].copyFrom(coords[i]);}
        r.downTime=down;r.eventTime=time;r.metaState=meta;r.buttonState=buttons;r.xPrecision=xp;r.yPrecision=yp;
        r.deviceId=device;r.edgeFlags=edges;r.source=src;r.flags=eventFlags;return r;
    }
    public int getAction(){return action;}
    public int getActionMasked(){return action&255;}
    public int getActionIndex(){return (action>>8)&255;}
    public void setAction(int value){if(recycled)throw new IllegalStateException("recycled event");action=value;}
    public int getPointerCount(){return ids.length;}
    public int getPointerId(int i){return ids[i];}
    public float getX(){return getX(0);}
    public float getY(){return getY(0);}
    public float getX(int i){return x[i];}
    public float getY(int i){return y[i];}
    public float getRawX(){return rawX;}
    public float getRawY(){return rawY;}
    public int getHistorySize(){return hx.length;}
    public float getHistoricalX(int pointer,int history){return hx[history][pointer];}
    public float getHistoricalY(int pointer,int history){return hy[history][pointer];}
    public void getPointerProperties(int i,PointerProperties out){out.copyFrom(properties[i]);}
    public void getPointerCoords(int i,PointerCoords out){out.copyFrom(coordinates[i]);out.x=x[i];out.y=y[i];}
    public long getDownTime(){return downTime;}
    public long getEventTime(){return eventTime;}
    public int getMetaState(){return metaState;}
    public int getButtonState(){return buttonState;}
    public float getXPrecision(){return xPrecision;}
    public float getYPrecision(){return yPrecision;}
    public int getDeviceId(){return deviceId;}
    public int getEdgeFlags(){return edgeFlags;}
    public int getSource(){return source;}
    public int getFlags(){return flags;}
    public void testRawOrigin(float left,float top){rawX=x[0]+left;rawY=y[0]+top;}
    public void offsetLocation(float dx,float dy){
        for(int i=0;i<x.length;i++){x[i]+=dx;y[i]+=dy;}
        for(int h=0;h<hx.length;h++)for(int i=0;i<x.length;i++){hx[h][i]+=dx;hy[h][i]+=dy;}
    }
    public void recycle(){if(recycled)throw new IllegalStateException("double recycle");recycled=true;}
}
