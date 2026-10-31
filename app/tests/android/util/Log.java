package android.util;

/** Host-only Android log double for the Java GL persistence regression. */
public final class Log {
    public static int i(String tag, String text) { return 0; }
    public static int e(String tag, String text, Throwable error) { return 0; }
}
