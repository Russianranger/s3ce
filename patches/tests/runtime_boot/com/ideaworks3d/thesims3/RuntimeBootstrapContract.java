package com.ideaworks3d.thesims3;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

/** Real production Java; Android, preferences and unavailable native library are host boundaries. */
public final class RuntimeBootstrapContract {
    private static int checks;
    private static void check(boolean value, String why) {
        checks++;
        if (!value) throw new AssertionError(why);
    }
    private static RuntimeBootstrap runtime() throws Exception {
        Field field=GameBootActivity.class.getDeclaredField("runtime");
        field.setAccessible(true);
        return (RuntimeBootstrap)field.get(null);
    }
    private static void assertFailureUi(Activity activity, String message) {
        check(activity.content instanceof LinearLayout, "observable startup failure UI");
        LinearLayout layout=(LinearLayout)activity.content;
        check(layout.children.size()==2 && layout.children.get(0) instanceof TextView
                && ((TextView)layout.children.get(0)).text.toString().contains(message), "specific failure retained");
        check(layout.children.get(1) instanceof Button, "diagnostics remain accessible");
        layout.children.get(1).listener.onClick(layout.children.get(1));
        check(GameDiagnostics.reportOpens>0, "report action remains connected");
    }
    private static long phaseCount(String exact) {
        return GameSession.phases.stream().filter(exact::equals).count();
    }
    private static void gate() throws Throwable {
        RuntimeBootstrap owner=new RuntimeBootstrap();
        AtomicInteger initializations=new AtomicInteger();
        check(!owner.isReady(), "new process has no native readiness");
        owner.ensure(true, () -> {
            check(!owner.isReady(), "readiness not published during initialization");
            initializations.incrementAndGet();
        });
        owner.ensure(true, () -> { throw new AssertionError("duplicate bootstrap"); });
        check(owner.isReady() && initializations.get()==1, "one completed owner initialization");
        try { owner.ensure(false, () -> { throw new AssertionError("unsafe live mode change"); });
            throw new AssertionError("mode conflict accepted");
        } catch (IllegalStateException expected) {
            check(expected.getMessage().contains("Fully close"), "explicit mode-change error");
        }
        check(owner.isReady(), "mode conflict does not invalidate another live runtime");
        RuntimeBootstrap failed=new RuntimeBootstrap();
        Throwable sentinel=new UnsatisfiedLinkError("native initialization failed");
        for (int attempt=0;attempt<2;attempt++) {
            try { failed.ensure(true, () -> { initializations.incrementAndGet(); throw sentinel; });
                throw new AssertionError("failed bootstrap accepted");
            } catch (Throwable actual) { check(actual==sentinel, "original initialization failure preserved"); }
            check(!failed.isReady(), "failure never publishes native readiness");
        }
        check(initializations.get()==2, "failed native image not retried in process");
        RuntimeBootstrap recursive=new RuntimeBootstrap();
        try { recursive.ensure(true, () -> recursive.ensure(true, () -> { }));
            throw new AssertionError("reentrant initialization accepted");
        } catch (IllegalStateException expected) {
            check(expected.getMessage().contains("in progress"), "reentrant bootstrap rejected");
        }
        check(!recursive.isReady(), "recursive initialization cannot publish readiness");

        RuntimeBootstrap concurrent=new RuntimeBootstrap();
        AtomicInteger concurrentCalls=new AtomicInteger();
        CountDownLatch start=new CountDownLatch(1);
        List<Thread> threads=new ArrayList<>();
        List<Throwable> errors=java.util.Collections.synchronizedList(new ArrayList<>());
        for (int index=0;index<16;index++) {
            Thread thread=new Thread(() -> {
                try { start.await(); concurrent.ensure(true, () -> { concurrentCalls.incrementAndGet(); Thread.sleep(10); }); }
                catch (Throwable error) { errors.add(error); }
            });
            threads.add(thread);thread.start();
        }
        start.countDown();for(Thread thread:threads)thread.join();
        check(errors.isEmpty() && concurrentCalls.get()==1 && concurrent.isReady(), "concurrent entry bootstraps once");
    }
    private static void readyEntry(boolean graphics) throws Throwable {
        // Model a successfully registered JNI boundary; execute the real owner/admission Java.
        runtime().ensure(graphics, () -> { });
        CompatActivity.fallback=graphics;
        Activity main=new Activity();
        check(!GameBootActivity.canStartMain(main), "process readiness alone cannot admit another Activity");
        check(GameBootActivity.prepareMain(main), "restored Activity admitted after process readiness");
        check(GameBootActivity.canStartMain(main), "prepared Main may reach original native thread");
        check(main.intent.hasExtra(GameBootActivity.EXTRA_GRAPHICS_COMPATIBILITY)
                && main.intent.getBooleanExtra(GameBootActivity.EXTRA_GRAPHICS_COMPATIBILITY,!graphics)==graphics,
                "resolved rendering mode preserved in restored Main intent");
        check(phaseCount("nativeBootstrap ENTER")==0, "ready Main entry does not bootstrap again");
        Activity foreign=new Activity();
        check(!GameBootActivity.canStartMain(foreign), "admission belongs to the prepared Activity only");

        GameBootActivity boot=new GameBootActivity();
        boot.intent.putExtra(GameBootActivity.EXTRA_GRAPHICS_COMPATIBILITY,graphics);
        boot.onCreate(new Bundle());
        check(boot.finished && boot.launched!=null && boot.launched.target.equals("com.ideaworks3d.thesims3.Main"),
                "ordinary Boot still starts original Main and finishes");
        check(boot.launched.getBooleanExtra(GameBootActivity.EXTRA_GRAPHICS_COMPATIBILITY,!graphics)==graphics,
                "normal Boot forwards both rendering modes");
        check((boot.launched.flags & (Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP))
                == (Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP), "original task flags preserved");

        Activity conflict=new Activity();
        conflict.intent.putExtra(GameBootActivity.EXTRA_GRAPHICS_COMPATIBILITY,!graphics);
        check(!GameBootActivity.prepareMain(conflict), "mode conflict is an explicit failed entry");
        check(runtime().isReady() && !GameBootActivity.canStartMain(conflict),
                "failed Activity cannot start thread even while process JNI remains ready");
        check(GameBootActivity.canStartMain(main), "failure cannot revoke another Activity's correct entry");
        assertFailureUi(conflict,"Fully close");
    }
    private static void unavailableLibrary(boolean bootEntry) throws Throwable {
        Activity main=bootEntry?new GameBootActivity():new Activity();
        if(bootEntry)((GameBootActivity)main).onCreate(new Bundle());
        else check(!GameBootActivity.prepareMain(main), "unavailable JNI is not a successful restored entry");
        check(!runtime().isReady() && !GameBootActivity.canStartMain(main), "failed initialization blocks native consumer");
        assertFailureUi(main,"UnsatisfiedLinkError");
        check(phaseCount("System.loadLibrary airplay ENTER")==1 && phaseCount("nativeBootstrap ENTER")==0,
                "failure occurs at original library boundary without bootstrap/native thread");
        check(!GameBootActivity.prepareMain(main), "subsequent entry preserves cached failure");
        check(phaseCount("System.loadLibrary airplay ENTER")==1, "partially initialized runtime not retried");
        check(!main.finished && main.launched==null, "failure shows diagnostics, without restart/redirect");
    }
    public static void main(String[] args) throws Throwable {
        switch(args[0]) {
            case "gate":gate();break;
            case "normal":readyEntry(true);break;
            case "original":readyEntry(false);break;
            case "restored-failure":unavailableLibrary(false);break;
            case "boot-failure":unavailableLibrary(true);break;
            default:throw new AssertionError("Unknown scenario");
        }
        System.out.println("PASS host bootstrap scenario="+args[0]+" assertions="+checks);
    }
}
