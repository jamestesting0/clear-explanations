import java.lang.management.ManagementFactory;
import java.util.concurrent.CountDownLatch;

class A19_fixture {
    static final Object left = new Object();
    static final Object right = new Object();
    static final CountDownLatch holdingFirst = new CountDownLatch(2);
    static void transfer(Object first, Object second) {
        synchronized (first) {
            holdingFirst.countDown();
            try { holdingFirst.await(); }
            catch (InterruptedException e) { throw new RuntimeException(e); }
            synchronized (second) {
                System.out.println("transfer-completed");
            }
        }
    }
    public static void main(String[] args) throws Exception {
        Thread a = new Thread(() -> transfer(left, right), "A");
        Thread b = new Thread(() -> transfer(left, right), "B");
        a.setDaemon(true);
        b.setDaemon(true);
        a.start(); b.start();
        for (int i = 0; i < 2000; i++) {
            if ((a.getState() == Thread.State.BLOCKED && b.getState() == Thread.State.WAITING) || (b.getState() == Thread.State.BLOCKED && a.getState() == Thread.State.WAITING))
                break;
            Thread.sleep(1);
        }
        long[] deadlocked = ManagementFactory.getThreadMXBean().findMonitorDeadlockedThreads();
        String[] states = {a.getState().toString(), b.getState().toString()}; java.util.Arrays.sort(states); System.out.println("states=" + String.join(",", states));
        System.out.println("deadlocked=" + (deadlocked == null ? 0 : deadlocked.length));
    }
}
