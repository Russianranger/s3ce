import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public final class LifecycleRace {
    static final class Bridge {
        final Object resume = new Object();
        boolean pauseRequested = true;
        final CountDownLatch teardown = new CountDownLatch(1);
        final CountDownLatch ready = new CountDownLatch(1);
        final CountDownLatch complete = new CountDownLatch(1);
        Thread start(boolean predicate) {
            Thread t = new Thread(() -> {
                try {
                    teardown.await();
                    synchronized (resume) {
                        ready.countDown();
                        if (predicate) {
                            while (pauseRequested) resume.wait();
                        } else resume.wait();
                    }
                    complete.countDown();
                } catch (InterruptedException ignored) {}
            });
            t.setDaemon(true);
            t.start();
            return t;
        }
        void resume() {
            synchronized (resume) {
                pauseRequested = false;
                resume.notifyAll();
            }
        }
    }
    static void earlyResume(boolean predicate, boolean expectComplete) throws Exception {
        Bridge b = new Bridge();
        Thread worker = b.start(predicate);
        b.resume();
        b.teardown.countDown();
        boolean complete = b.complete.await(250, TimeUnit.MILLISECONDS);
        if (complete != expectComplete) throw new AssertionError("early resume " + predicate);
        worker.interrupt();
        worker.join(1000);
    }
    public static void main(String[] args) throws Exception {
        earlyResume(false, false);
        earlyResume(true, true);
        Bridge b = new Bridge();
        Thread worker = b.start(true);
        b.teardown.countDown();
        if (!b.ready.await(1, TimeUnit.SECONDS)) throw new AssertionError("not waiting");
        synchronized (b.resume) { b.resume.notifyAll(); }
        if (b.complete.await(100, TimeUnit.MILLISECONDS)) throw new AssertionError("spurious wake resumes game");
        b.resume();
        if (!b.complete.await(1, TimeUnit.SECONDS)) throw new AssertionError("normal resume hangs");
        worker.join(1000);
        final Object pause = new Object();
        final CountDownLatch pauseWaiting = new CountDownLatch(1);
        Thread stalledGame = new Thread(() -> {
            synchronized (pause) {
                pauseWaiting.countDown();
                try { pause.wait(250); } catch (InterruptedException ignored) {}
            }
        });
        stalledGame.setDaemon(true);
        stalledGame.start();
        if (!pauseWaiting.await(1, TimeUnit.SECONDS)) throw new AssertionError("pause wait not entered");
        stalledGame.join(1500);
        if (stalledGame.isAlive()) throw new AssertionError("timed pause wait never returned");
        System.out.println("PASS: original early-notify race reproduced; predicate skips lost wake, resists spurious wake, resumes normally; 250ms wait returns without game notification.");
    }
}
