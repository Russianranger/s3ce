package com.ideaworks3d.thesims3;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Comparator;

/** Bounded diagnostic history. Only the game process owns rotation and writes. */
public final class SessionDiagnostics {
    private static final String SESSION_LOG = "compat-session.log";
    private static final String HISTORY = "compat-sessions";
    private static final int HISTORY_COUNT = 4;
    private static final int LOG_LIMIT = 32768;
    private static final String[] GAME_LOGS = {SESSION_LOG, "compat-boot.log", "compat-native.log",
            "compat-events.log", "compat-java-gl.log", "compat-java-crash.log"};
    private final File directory;
    private boolean begun;

    public SessionDiagnostics(File directory) { this.directory = directory; }

    /** Invoke once per game process, before legacy/native logs can be truncated. */
    public synchronized void begin(String identity, long wallTime, long elapsedTime, int pid) throws IOException {
        if (begun) return;
        begun = true;
        String rotationFailure = null;
        try { archive(wallTime, pid); }
        catch (IOException error) { rotationFailure = error.toString(); }
        append("SESSION " + identity + " pid=" + pid + " wallMs=" + wallTime
                + " elapsedMs=" + elapsedTime + "\n");
        if (rotationFailure != null) append("Diagnostic history incomplete: " + rotationFailure + "\n");
    }

    public synchronized void phase(String phase, long wallTime, long elapsedTime) throws IOException {
        append("wallMs=" + wallTime + " elapsedMs=" + elapsedTime + " " + phase + "\n");
    }

    private void append(String text) throws IOException {
        File file = new File(directory, SESSION_LOG);
        // Keep the original identity even during a long session with many transitions.
        int remaining = (int) Math.max(0, LOG_LIMIT - file.length());
        if (remaining == 0) return;
        try (FileOutputStream output = new FileOutputStream(file, true)) {
            byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
            output.write(bytes, 0, Math.min(bytes.length, remaining));
            output.getFD().sync();
        }
    }

    private void archive(long wallTime, int pid) throws IOException {
        boolean any = false;
        for (String name : GAME_LOGS) if (new File(directory, name).isFile()) any = true;
        if (!any) return;
        File history = new File(directory, HISTORY);
        if (!history.isDirectory() && !history.mkdirs()) throw new IOException("Cannot create session history");
        File destination = new File(history, "before-" + wallTime + "-" + pid);
        for (int suffix = 1; destination.exists(); suffix++)
            destination = new File(history, "before-" + wallTime + "-" + pid + "-" + suffix);
        if (!destination.mkdir()) throw new IOException("Cannot create previous-session snapshot");
        // Copy first, then retire only after every bounded copy is durable. A
        // failed copy leaves originals intact and its snapshot visibly incomplete.
        for (String name : GAME_LOGS) {
            File source = new File(directory, name);
            if (!source.isFile()) continue;
            byte[] bytes = tail(source, name.equals("compat-native.log") ? 131072 : LOG_LIMIT);
            try (FileOutputStream output = new FileOutputStream(new File(destination, name))) {
                output.write(bytes);
                output.getFD().sync();
            }
        }
        try (FileOutputStream output = new FileOutputStream(new File(destination, "complete"))) {
            output.write("Previous logs copied before this game process began.\n".getBytes(StandardCharsets.UTF_8));
            output.getFD().sync();
        }
        for (String name : GAME_LOGS) {
            File source = new File(directory, name);
            if (source.isFile() && !source.delete()) throw new IOException("Cannot retire archived log " + name);
        }
        File[] snapshots = snapshots(history);
        for (int i = HISTORY_COUNT; i < snapshots.length; i++) deleteSnapshot(snapshots[i]);
    }

    private static byte[] tail(File file, int limit) throws IOException {
        try (RandomAccessFile input = new RandomAccessFile(file, "r")) {
            int length = (int) Math.min(input.length(), limit);
            input.seek(input.length() - length);
            byte[] bytes = new byte[length];
            input.readFully(bytes);
            return bytes;
        }
    }

    private static File[] snapshots(File history) {
        File[] files = history.listFiles(file -> file.isDirectory() && file.getName().startsWith("before-"));
        if (files == null) return new File[0];
        Arrays.sort(files, Comparator.comparingLong(SessionDiagnostics::snapshotTime).reversed()
                .thenComparing(File::getName));
        return files;
    }

    private static long snapshotTime(File file) {
        try { return Long.parseLong(file.getName().split("-", 4)[1]); }
        catch (RuntimeException error) { return Long.MIN_VALUE; }
    }

    private static void deleteSnapshot(File snapshot) throws IOException {
        File[] files = snapshot.listFiles();
        if (files == null) throw new IOException("Cannot inspect old diagnostic snapshot");
        for (File file : files) if (!file.delete()) throw new IOException("Cannot remove old diagnostic snapshot file");
        if (!snapshot.delete()) throw new IOException("Cannot remove old diagnostic snapshot");
    }

    /** Read-only: the launcher never rotates logs belonging to a live game. */
    public static void appendReport(File directory, StringBuilder report) {
        report.append("\nCurrent game-session identity/phases:\n");
        appendFile(new File(directory, SESSION_LOG), report, LOG_LIMIT);
        report.append("\nPrevious game sessions (newest first; up to four; bounded log tails):\n");
        File[] snapshots = snapshots(new File(directory, HISTORY));
        if (snapshots.length == 0) report.append("No archived sessions. Older builds did not retain retry logs.\n");
        for (int i = 0; i < Math.min(HISTORY_COUNT, snapshots.length); i++) {
            File snapshot = snapshots[i];
            report.append("\n--- ").append(snapshot.getName())
                    .append(new File(snapshot, "complete").isFile() ? " ---\n" : " [INCOMPLETE SNAPSHOT] ---\n");
            for (String name : GAME_LOGS) {
                File file = new File(snapshot, name);
                if (!file.isFile()) continue;
                report.append(name).append(":\n");
                appendFile(file, report, name.equals("compat-native.log") ? 65536
                        : name.equals(SESSION_LOG) ? LOG_LIMIT : 8192);
            }
        }
    }

    private static void appendFile(File file, StringBuilder report, int limit) {
        try {
            if (file.length() > limit) report.append("[Earlier bytes omitted; showing final ").append(limit).append(" bytes]\n");
            report.append(new String(tail(file, limit), StandardCharsets.UTF_8)).append('\n');
        } catch (IOException error) { report.append("Unavailable: ").append(error).append('\n'); }
    }
}
