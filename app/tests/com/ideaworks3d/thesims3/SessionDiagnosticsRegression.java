package com.ideaworks3d.thesims3;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
/** Production rotation/export against real files; no engine fixture. */
public final class SessionDiagnosticsRegression {
    static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    static void write(File directory, String name, String text) throws Exception {
        Files.write(new File(directory, name).toPath(), text.getBytes(StandardCharsets.UTF_8));
    }
    static String read(File file) throws Exception {
        return new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
    }
    static File[] snapshots(File directory) {
        File[] files = new File(directory, "compat-sessions").listFiles(File::isDirectory);
        return files == null ? new File[0] : files;
    }
    public static void main(String[] args) throws Exception {
        File directory = Files.createTempDirectory("s3ce-session-test-").toFile();
        write(directory, "save.dat", "existing-user-save");
        write(directory, "compat-boot.log", "S3CE 0.1.11 boot pid=11\n");
        char[] large = new char[300000]; Arrays.fill(large, 'x');
        write(directory, "compat-native.log", new String(large) + "old-native-tail\n");
        SessionDiagnostics first = new SessionDiagnostics(directory);
        first.begin("version=0.1.12 code=112", 1000, 40, 12);
        require(snapshots(directory).length == 1, "migrate before reset");
        File prior = snapshots(directory)[0];
        require(read(new File(prior, "compat-boot.log")).contains("0.1.11"), "old version retained");
        require(new File(prior, "compat-native.log").length() == 131072, "native history bounded");
        require(read(new File(prior, "compat-native.log")).endsWith("old-native-tail\n"), "native tail");
        require(!new File(directory, "compat-native.log").exists(), "fresh native log");
        require(read(new File(directory, "save.dat")).equals("existing-user-save"), "save untouched");
        first.phase("nativeBootstrap ENTER", 1001, 41);
        first.begin("must-not-reinitialize", 1002, 42, 12);
        require(snapshots(directory).length == 1, "begin idempotent");
        SessionDiagnostics second = new SessionDiagnostics(directory);
        second.begin("version=0.1.12 code=112", 2000, 50, 13);
        second.phase("successful retry", 2001, 51);
        StringBuilder report = new StringBuilder();
        SessionDiagnostics.appendReport(directory, report);
        require(report.toString().contains("pid=12") && report.toString().contains("nativeBootstrap ENTER"), "failed attempt retained");
        require(report.toString().contains("pid=13") && report.toString().contains("successful retry"), "retry separately attributed");
        require(report.toString().contains("0.1.11"), "legacy export");
        String before = read(new File(directory, "compat-session.log"));
        SessionDiagnostics.appendReport(directory, new StringBuilder());
        require(before.equals(read(new File(directory, "compat-session.log"))) && snapshots(directory).length == 2, "report read-only");
        for (int i = 3; i <= 8; i++) new SessionDiagnostics(directory).begin("code=112", i * 1000, i * 10, 10 + i);
        require(snapshots(directory).length == 4, "four prior processes retained");
        for (File snapshot : snapshots(directory)) require(new File(snapshot, "complete").isFile(), "completed snapshot");
        SessionDiagnostics bounded = new SessionDiagnostics(directory);
        bounded.begin("identity-kept-at-head", 9000, 100, 19);
        bounded.phase(new String(large), 9001, 101);
        bounded.phase("beyond bound", 9002, 102);
        File current = new File(directory, "compat-session.log");
        require(current.length() == 32768, "session bounded for oversized message");
        require(read(current).startsWith("SESSION identity-kept-at-head"), "identity retained");
        new SessionDiagnostics(directory).begin("next-process", 10000, 110, 20);
        report = new StringBuilder(); SessionDiagnostics.appendReport(directory, report);
        require(report.toString().contains("identity-kept-at-head"), "previous identity exported");
        File failed = Files.createTempDirectory("s3ce-session-failure-").toFile();
        write(failed, "compat-sessions", "not-a-directory");
        write(failed, "compat-native.log", "old evidence");
        new SessionDiagnostics(failed).begin("new-process", 11000, 120, 21);
        require(read(new File(failed, "compat-native.log")).equals("old evidence"), "failure preserves originals");
        require(read(new File(failed, "compat-session.log")).contains("Diagnostic history incomplete:"), "failure reported");
        require(ExitReport.reasonName(3).equals("LOW_MEMORY"), "reason3 LOW_MEMORY");
        require(ExitReport.reasonName(1).equals("EXIT_SELF"), "reason1 EXIT_SELF");
        require(ExitReport.reasonName(5).equals("CRASH_NATIVE"), "reason5 CRASH_NATIVE");
        require(ExitReport.reasonName(1000).equals("UNRECOGNIZED"), "unknown reason");
        System.out.println("Session diagnostics migration/retry/retention/export/save/failure/exit-label checks passed");
    }
}
