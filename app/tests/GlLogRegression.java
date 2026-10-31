package com.ideaworks3d.thesims3;

import java.io.File;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/** Exercises the real logger, including fallback after an unwritable path. */
public final class GlLogRegression {
    public static void main(String[] args) throws Exception {
        File directory = Files.createTempDirectory("s3ce-gl-log-").toFile();
        File target = new File(directory, "compat-java-gl.log");
        Field file = GameDiagnostics.class.getDeclaredField("glLogFile");
        file.setAccessible(true);
        try {
            file.set(null, target);
            GameDiagnostics.recordGlEntry(1, false, Boolean.FALSE, Boolean.FALSE);
            Throwable original = new IllegalStateException("EGL setup failed", new RuntimeException("driver failure"));
            GameDiagnostics.recordGlFailure(original);
            GameDiagnostics.recordGlExit(1, true, Boolean.FALSE, Boolean.FALSE);
            String text = new String(Files.readAllBytes(target.toPath()), StandardCharsets.UTF_8);
            for (String expected : new String[]{"ENTRY version=1 useGL=false", "javaThread=", "name=",
                    "Java GL bridge FAILURE", "IllegalStateException: EGL setup failed",
                    "Caused by: java.lang.RuntimeException: driver failure", "GlLogRegression.main",
                    "EXIT version=1 useGL=true"})
                if (!text.contains(expected)) throw new AssertionError("Missing persisted detail: " + expected);
            file.set(null, directory); // Opening a directory as a file must fail harmlessly.
            GameDiagnostics.recordGlFailure(original);
            GameDiagnostics.recordGlEntry(1, false, new Object() {
                @Override public String toString() { throw new AssertionError("bad diagnostic value"); }
            }, null);
            System.out.println("PASS: real GL logger persists entry/exit, complete cause stack, and never propagates logging failures.");
        } finally {
            file.set(null, null);
            Files.deleteIfExists(target.toPath());
            Files.deleteIfExists(directory.toPath());
        }
    }
}
