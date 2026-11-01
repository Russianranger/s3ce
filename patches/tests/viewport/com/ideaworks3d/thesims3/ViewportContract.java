package com.ideaworks3d.thesims3;

import android.app.Activity;
import android.graphics.Color;
import android.os.Build;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import java.io.File;
import java.util.ArrayList;
import java.util.List;

/** Executes production GameViewport. Framework and Surface behavior are fixtures. */
public final class ViewportContract {
    private static int assertions;
    private static void check(boolean yes,String reason){assertions++;if(!yes)throw new AssertionError(reason);}
    private static void same(float expected,float actual,String reason){check(Math.abs(expected-actual)<.0001f,reason+": "+expected+" != "+actual);}
    private static final class Child extends View {
        final List<MotionEvent> events=new ArrayList<>();
        Child(Activity activity){super(activity);}
        @Override public boolean onTouchEvent(MotionEvent event){events.add(MotionEvent.obtain(event));return true;}
        int cancels(){int n=0;for(MotionEvent e:events)if(e.getActionMasked()==MotionEvent.ACTION_CANCEL)n++;return n;}
        MotionEvent last(){return events.get(events.size()-1);}
        void clear(){for(MotionEvent e:events)e.recycle();events.clear();}
    }
    private static final class Fixture {
        final Activity activity;
        final Child child;
        final GameViewport root;
        Fixture(File files,int width,int height,int x,int y){
            activity=new Activity(files);child=new Child(activity);
            GameViewport.install(activity,child);root=(GameViewport)activity.content;
            layout(width,height,x,y);
        }
        void layout(int width,int height,int x,int y){
            root.measure(View.MeasureSpec.makeMeasureSpec(width,View.MeasureSpec.EXACTLY),
                         View.MeasureSpec.makeMeasureSpec(height,View.MeasureSpec.EXACTLY));
            root.layout(x,y,x+width,y+height);
        }
        void send(int action,float x,float y){root.dispatchTouchEvent(event(action,new int[]{7},new float[]{x},new float[]{y}));}
        void down(){send(MotionEvent.ACTION_DOWN,child.getLeft()+12,child.getTop()+34);}
        void up(){send(MotionEvent.ACTION_UP,child.getLeft()+12,child.getTop()+34);}
        void recovered(){int n=child.events.size();down();up();check(child.events.size()==n+2,"new gesture recovered");}
    }
    private static MotionEvent event(int action,int[] ids,float[] x,float[] y){return new MotionEvent(action,ids,x,y,new float[0][],new float[0][]);}
    private static void rect(GameViewport.Bounds b,int left,int top,int width,int height){
        check(b.left==left&&b.top==top&&b.width==width&&b.height==height,"expected rectangle");
        check((long)b.width*9==(long)b.height*16,"exact16:9");
    }
    private static void geometry(File files){
        rect(GameViewport.fit(2640,1080),360,0,1920,1080);
        rect(GameViewport.fit(2641,1081),360,0,1920,1080);
        rect(GameViewport.fit(2640,1007),432,4,1776,999);
        rect(GameViewport.fit(2640,1019),416,1,1808,1017);
        rect(GameViewport.fit(2500,1007),362,4,1776,999);
        rect(GameViewport.fit(1920,1080),0,0,1920,1080);
        rect(GameViewport.fit(1080,2640),4,1018,1072,603);
        rect(GameViewport.fit(-1,9),0,4,0,0);
        Fixture f=new Fixture(files,2500,1007,123,33);
        // This content already excludes asymmetric decor insets. The still
        // nonzero root-inset object must not be subtracted for a second time.
        f.root.testSetRootInsets(new int[]{123,33,17,40});
        f.layout(2500,1007,123,33);
        check(View.insetReads==0,"already fitted content never reads insets twice");
        check(f.child.getMeasuredWidth()==1776&&f.child.getMeasuredHeight()==999,"measured actual child dimensions");
        check(f.child.getWidth()==1776&&f.child.getHeight()==999,"laid-out actual child dimensions");
        int[] screen=new int[2];f.child.getLocationOnScreen(screen);
        check(screen[0]==485&&screen[1]==37,"nonzero decor/screen origin");
        f.down();f.up();same(12,f.child.events.get(0).getX(0),"origin subtracted once");same(34,f.child.events.get(0).getY(0),"vertical origin once");
        check(!f.root.splitting,"all sparse pointer IDs share original bridge");
    }
    private static void window(File files){
        Fixture f=new Fixture(files,2640,1080,0,0);Window w=f.activity.getWindow();
        check(f.root.getWidth()==2640&&f.root.getHeight()==1080,"whole fitted content retained");
        check(f.child.getLeft()==360&&f.child.getTop()==0&&f.child.getWidth()==1920&&f.child.getHeight()==1080,"actual centered1920x1080 child");
        check(f.child.getMeasuredWidth()==1920&&f.child.getMeasuredHeight()==1080,"surface measured1920x1080");
        check((w.flags&WindowManager.LayoutParams.FLAG_FULLSCREEN)!=0,"fullscreen");
        check(w.statusColor==Color.BLACK&&w.navigationColor==Color.BLACK,"black system surfaces");
        check(w.background==android.R.color.black&&f.root.background==Color.BLACK,"black margin/window");
        check(w.decorCalls==(Build.VERSION.SDK_INT>=30?1:0),"only supported decor-fit call");
        if(Build.VERSION.SDK_INT>=30)check(w.decorFits,"decor fits safe content");
        check(w.attributeCalls==(Build.VERSION.SDK_INT>=28?1:0),"only supported cutout call");
        if(Build.VERSION.SDK_INT>=28)check(w.getAttributes().layoutInDisplayCutoutMode==WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_NEVER,"cutout never");
        try{GameViewport.install(null,f.child);throw new AssertionError("null activity");}catch(IllegalArgumentException expected){assertions++;}
        try{GameViewport.install(f.activity,null);throw new AssertionError("null child");}catch(IllegalArgumentException expected){assertions++;}
    }
    private static void input(File files){
        Fixture f=new Fixture(files,2640,1007,37,19);int l=f.child.getLeft(),t=f.child.getTop();
        f.down();
        f.root.dispatchTouchEvent(event(MotionEvent.ACTION_POINTER_DOWN|(1<<8),new int[]{7,29},new float[]{l+12,l+70},new float[]{t+34,t+80}));
        MotionEvent move=new MotionEvent(MotionEvent.ACTION_MOVE,new int[]{7,29},new float[]{l+13,l+71},new float[]{t+35,t+81},
            new float[][]{{l+11,l+69},{l+12,l+70}},new float[][]{{t+33,t+79},{t+34,t+80}});
        f.root.dispatchTouchEvent(move);MotionEvent local=f.child.last();
        check(local.getPointerId(0)==7&&local.getPointerId(1)==29,"sparse IDs unchanged");
        same(13,local.getX(0),"primary child-local X");same(71,local.getX(1),"secondary child-local X");
        same(35,local.getY(0),"primary child-local Y");same(81,local.getY(1),"secondary child-local Y");
        check(local.getHistorySize()==2,"history retained");same(11,local.getHistoricalX(0,0),"history primary translated once");same(70,local.getHistoricalX(1,1),"history secondary translated once");same(33,local.getHistoricalY(0,0),"historical primary Y once");same(80,local.getHistoricalY(1,1),"historical secondary Y once");
        same(l+13,move.getX(0),"original event unmodified");same(l+69,move.getHistoricalX(1,0),"original history unmodified");
        f.root.dispatchTouchEvent(event(MotionEvent.ACTION_POINTER_UP|(1<<8),new int[]{7,29},new float[]{l+13,l+71},new float[]{t+35,t+81}));
        check(f.child.last().getActionIndex()==1&&f.child.last().getPointerCount()==2,"pointer-up index retained");f.up();
        check(f.child.cancels()==0,"normal input not canceled");f.child.clear();
        f.send(MotionEvent.ACTION_DOWN,l+f.child.getWidth(),t+34);f.up();
        check(f.child.events.isEmpty(),"right margin down inert");
        f.send(MotionEvent.ACTION_DOWN,l+12,t-1);f.up();check(f.child.events.isEmpty(),"top margin down inert");
        f.send(MotionEvent.ACTION_DOWN,l+12,t+f.child.getHeight());f.up();check(f.child.events.isEmpty(),"bottom margin down inert");
        f.send(MotionEvent.ACTION_DOWN,l-1,t+34);f.send(MotionEvent.ACTION_MOVE,l+12,t+34);f.up();
        check(f.child.events.isEmpty(),"margin-born gesture stays inert");f.recovered();f.child.clear();
        f.down();f.root.dispatchTouchEvent(event(MotionEvent.ACTION_POINTER_DOWN|(1<<8),new int[]{7,29},new float[]{l+12,l+70},new float[]{t+34,t+80}));
        f.root.dispatchTouchEvent(event(MotionEvent.ACTION_MOVE,new int[]{7,29},new float[]{l+12,l+f.child.getWidth()},new float[]{t+34,t+80}));
        check(f.child.events.size()==3&&f.child.cancels()==1,"secondary leaving sends one cancel");
        check(f.child.last().getPointerCount()==2&&f.child.last().getPointerId(1)==29,"cancel retains every pointer");
        same(70,f.child.last().getX(1),"cancel uses previous valid child space");
        f.send(MotionEvent.ACTION_MOVE,l+12,t+34);f.up();check(f.child.events.size()==3,"reentry swallowed until up");f.recovered();f.child.clear();
        f.down();f.send(MotionEvent.ACTION_CANCEL,l+12,t+34);f.send(MotionEvent.ACTION_CANCEL,l+12,t+34);
        check(f.child.cancels()==1,"explicit cancel once");f.recovered();f.child.clear();
        f.down();f.send(MotionEvent.ACTION_CANCEL,l-2,t+34);check(f.child.cancels()==1,"outside cancel once");f.recovered();
    }
    private static void lifecycle(File files){
        Fixture f=new Fixture(files,2640,1080,37,19);
        f.down();f.root.onWindowFocusChanged(false);f.root.onWindowFocusChanged(false);
        check(f.child.cancels()==1,"focus loss cancels once");same(12,f.child.last().getX(0),"focus cancel local X");
        f.up();f.root.onWindowFocusChanged(true);f.recovered();f.child.clear();
        f.down();f.root.testVisibility(View.INVISIBLE);f.root.testVisibility(View.GONE);
        check(f.child.cancels()==1,"hidden window cancels once");f.up();f.root.testVisibility(View.VISIBLE);f.recovered();f.child.clear();
        f.down();f.root.testDetach();f.root.testDetach();check(f.child.cancels()==1,"detach cancels once");f.up();f.recovered();f.child.clear();
        f.down();f.layout(2500,1007,37,19);check(f.child.cancels()==1,"resize cancels");
        same(12,f.child.last().getX(0),"resize cancel uses previous bounds");same(34,f.child.last().getY(0),"resize cancel previous Y");
        check(f.child.getWidth()==1776&&f.child.getHeight()==999,"resize child dims");f.up();f.recovered();f.child.clear();
        f.down();f.layout(2500,1007,70,36);check(f.child.cancels()==1,"same-size screen-origin shift cancels");
        same(12,f.child.last().getX(0),"origin shift cancel child-local");f.up();f.recovered();f.child.clear();
        f.down();f.layout(2500,1007,70,36);check(f.child.cancels()==0,"unchanged relayout preserves gesture");f.up();
        f.down();Child next=new Child(f.activity);GameViewport.install(f.activity,next);
        check(f.child.cancels()==1,"software-to-GL content replacement cancels old child");
        check(((ViewGroup)f.activity.content).getChildAt(0)==next,"replacement owns new surface");
    }
    private static void historicalBoundary(File files){
        Fixture f=new Fixture(files,2640,1080,0,0);int l=f.child.getLeft(),t=f.child.getTop();f.down();
        MotionEvent crossed=new MotionEvent(MotionEvent.ACTION_MOVE,new int[]{7},new float[]{l+15},new float[]{t+34},
            new float[][]{{l-1},{l+14}},new float[][]{{t+34},{t+34}});
        f.root.dispatchTouchEvent(crossed);
        check(f.child.events.size()==2&&f.child.cancels()==1,"historical excursion into margin cancels before reentry");
        f.up();f.recovered();f.child.clear();
        f.down();f.root.dispatchTouchEvent(event(MotionEvent.ACTION_POINTER_DOWN|(1<<8),new int[]{7,29},new float[]{l+12,l+70},new float[]{t+34,t+80}));
        MotionEvent secondaryCrossed=new MotionEvent(MotionEvent.ACTION_MOVE,new int[]{7,29},new float[]{l+12,l+70},new float[]{t+34,t+80},
            new float[][]{{l+12,l-1}},new float[][]{{t+34,t+80}});
        f.root.dispatchTouchEvent(secondaryCrossed);
        check(f.child.events.size()==3&&f.child.cancels()==1,"secondary historical excursion cancels whole gesture");
        check(f.child.last().getPointerId(1)==29,"historical cancel retains secondary ID");f.up();f.recovered();
    }
    public static void main(String[] args){
        Build.VERSION.SDK_INT=Integer.parseInt(args[0]);
        File files=new File(System.getProperty("s3ce.viewport.work"),"sdk"+args[0]);check(files.mkdirs()||files.isDirectory(),"fixture log directory");
        geometry(files);window(files);input(files);lifecycle(files);historicalBoundary(files);
        System.out.println("{\"sdkContract\":"+Build.VERSION.SDK_INT+",\"assertions\":"+assertions+",\"passed\":true,\"boundary\":\"Android view/window/input doubles; no EGL, ART, hardware or native engine\"}");
    }
}
