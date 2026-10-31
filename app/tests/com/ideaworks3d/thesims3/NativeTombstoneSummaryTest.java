package com.ideaworks3d.thesims3;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;

/** Host JVM checks; no Android framework or protobuf runtime is required. */
public final class NativeTombstoneSummaryTest {
    private static int checks;

    public static void main(String[] args) {
        validCrashAndUnknownFields();
        armRegistersAndUnknownFields();
        registerBoundsAndMalformedFields();
        malformedInput();
        boundedOutputAndFramePriority();
        System.out.println("PASS: NativeTombstoneSummary " + checks + " checks");
    }

    private static void validCrashAndUnknownFields() {
        Proto ordinary = thread(88, "worker", 1);
        Proto crashing = thread(99, "game-main", 2);
        Proto signal = new Proto().number(1, 11).text(2, "SIGSEGV")
                .number(3, 1).text(4, "SEGV_MAPERR").number(8, 1).number(9, 0x1234);
        Proto map = new Proto().number(1, 0x1000).number(2, 0x3000)
                .number(6, 1).text(7, "[anon:legacy]");
        // Put thread/map messages before tid; protobuf fields are unordered.
        Proto tombstone = new Proto().message(16, entry(88, ordinary))
                .message(16, entry(99, crashing)).message(17, map)
                .text(4, "2026-10-30T19:00:00-0500").number(5, 123).number(6, 99)
                .message(10, signal).text(14, "abort\nmessage")
                .message(15, new Proto().text(1, "invalid memory access"))
                .number(1001, 42).fixed64(1002).text(1003, "UNKNOWN_SECRET")
                .fixed32(1004);
        String result = NativeTombstoneSummary.summarize(tombstone.bytes());
        contains(result, "PID: 123 TID: 99");
        contains(result, "SIGSEGV (11), SEGV_MAPERR (1), fault=0x1234");
        contains(result, "Abort: abort message");
        contains(result, "Cause: invalid memory access");
        contains(result, "Crashing thread 99 \"game-main\"");
        contains(result, "pc=0x2000 rel_pc=0x40 /data/libairplay.so (render+0x8)");
        contains(result, "[anon:legacy] base=0x1000 offset=0x1000");
        check(result.indexOf("Crashing thread") < result.indexOf("Other thread"), "crashing thread first");
        check(!result.contains("UNKNOWN_SECRET"), "unknown fields not exposed");
        check(!result.contains("MEMORY_SECRET"), "memory dumps not exposed");
        String zeroFault = NativeTombstoneSummary.summarize(new Proto()
                .message(10, new Proto().number(8, 1)).bytes());
        contains(zeroFault, "fault=0x0");
    }

    // Synthetic wire fixtures follow the pinned Android 13 AOSP schema:
    // https://android.googlesource.com/platform/system/core/+/refs/tags/android-13.0.0_r1/debuggerd/proto/tombstone.proto
    // Schema SHA256: 225912c9cb4fdfcbd24d3e9e20fccd51082b763bd78207768b72da32db1261db.
    private static void armRegistersAndUnknownFields() {
        Proto thread = thread(99, "ARM crash", 1);
        // A proto3 zero-valued register can omit field2 entirely.
        thread.message(3, new Proto().text(1, "r0"));
        for (int i = 1; i <= 12; i++) thread.message(3, register("r" + i, 0xc0000000L + i));
        thread.message(3, register("sp", 0xbffff000L))
                .message(3, register("lr", 0xc013b790L))
                .message(3, register("pc", 0xc013b784L))
                .message(3, register("cpsr", 0x60000010L));
        String result = crash(thread);
        contains(result, "r0=0x0 r1=0xc0000001");
        contains(result, "r12=0xc000000c sp=0xbffff000 lr=0xc013b790 pc=0xc013b784");
        contains(result, "cpsr=0x60000010");
        check(occurrences(result, "  Registers:") == 1, "one crashing register heading");
        check(result.indexOf("  Registers:") < result.indexOf("  #00"), "registers precede frames");
        check(!result.contains("REGISTER_SECRET"), "unknown register fields omitted");
        check(!result.contains("MEMORY_SECRET"), "register summary still skips memory bytes");
        Proto sparse = new Proto().number(1, 99).message(3, register("all64", -1L))
                .message(3, new Proto().number(2, Long.MIN_VALUE))
                .message(3, new Proto().text(1, "zero"));
        result = crash(sparse);
        contains(result, "all64=0xffffffffffffffff");
        contains(result, "(unnamed)=0x8000000000000000");
        contains(result, "zero=0x0");
        contains(result, "No backtrace frames recorded");
        Proto ordinary = thread(88, "other", 1).message(3, register("OTHER_REGISTER", 7));
        result = NativeTombstoneSummary.summarize(new Proto().number(6, 99)
                .message(16, entry(88, ordinary)).message(16, entry(99, thread)).bytes());
        check(!result.contains("OTHER_REGISTER"), "only crash registers retained");
        contains(result, "Other thread 88");
    }

    private static void registerBoundsAndMalformedFields() {
        Proto thread = new Proto().number(1, 99);
        for (int i = 0; i < 100; i++) thread.message(3, register("reg" + i, i));
        String result = crash(thread);
        check(occurrences(result, "=0x") == 32, "maximum 32 register entries");
        contains(result, "reg31=0x1f");
        check(!result.contains("reg32="), "extra registers omitted");
        String large = repeat("x", 1000);
        result = crash(new Proto().number(1, 99).message(3, register(large + "TAIL_SECRET", 42))
                .message(3, register("r0\nINJECT", 0)));
        contains(result, repeat("x", 32) + "…=0x2a");
        contains(result, "r0 INJECT=0x0");
        check(!result.contains("TAIL_SECRET"), "register name bounded");
        check(result.getBytes(StandardCharsets.UTF_8).length <= 12 * 1024, "register output bounded");
        malformed(crashBytes(new Proto().number(1, 99).number(3, 1)), "register message wrong wire");
        malformed(crashBytes(new Proto().number(1, 99).message(3, new Proto().number(1, 0))),
                "register name wrong wire");
        malformed(crashBytes(new Proto().number(1, 99).message(3, new Proto().text(2, "wrong"))),
                "register value wrong wire");
        malformed(crashBytes(new Proto().number(1, 99).raw(3, new byte[]{0x10, (byte) 0x80})),
                "truncated register value");
        thread.message(3, new Proto().text(2, "wrong"));
        malformed(crashBytes(thread), "malformed register beyond collection cap");
        Proto others = new Proto().number(6, 99);
        for (int i = 0; i < 5; i++) others.message(16, entry(i, thread(i, "other", 0)));
        others.message(16, entry(55, new Proto().message(3, new Proto().number(1, 1))));
        malformed(others.bytes(), "unselected thread register still validated");
        Proto verbose = new Proto().number(1, 99);
        for (int i = 0; i < 32; i++) verbose.message(3, register(large, -1L))
                .message(4, new Proto().text(4, large).text(6, large));
        result = crash(verbose);
        contains(result, "[Summary truncated]");
        check(result.getBytes(StandardCharsets.UTF_8).length <= 12 * 1024, "register and frame shared output budget");
    }

    private static Proto register(String name, long value) {
        // Reversed fields and unknown fields exercise legal wire ordering and skipping.
        return new Proto().number(2, value).text(1, name).number(1001, 7)
                .fixed64(1002).text(1003, "REGISTER_SECRET").fixed32(1004);
    }

    private static byte[] crashBytes(Proto thread) {
        return new Proto().number(6, 99).message(16, entry(99, thread)).bytes();
    }

    private static String crash(Proto thread) {
        return NativeTombstoneSummary.summarize(crashBytes(thread));
    }

    private static void malformedInput() {
        malformed(new byte[]{0}, "zero tag");
        malformed(new byte[]{(byte) 0x80}, "truncated tag");
        malformed(new byte[]{0x22, 5, 'x'}, "truncated string");
        malformed(new byte[]{0x28, (byte) 0x80}, "truncated value");
        malformed(new byte[]{0x23}, "group wire");
        malformed(new byte[]{0x21, 0, 0, 0, 0, 0, 0, 0, 0}, "known wrong wire");
        malformed(new byte[]{(byte) 0x82, 1, 2, 0x12, 1}, "truncated nested thread value");
        byte[] overflow = new byte[11];
        overflow[0] = 0x28;
        for (int i = 1; i < overflow.length; i++) overflow[i] = (byte) 0xff;
        malformed(overflow, "overflow varint");
        malformed(new byte[]{(byte) 0x91, 0x3f, 0}, "truncated unknown fixed64");
        malformed(new byte[]{(byte) 0x95, 0x3f, 0}, "truncated unknown fixed32");
        malformed(new byte[]{(byte) 0x92, 0x3f, (byte) 0xff, (byte) 0xff,
                (byte) 0xff, (byte) 0xff, 7}, "huge unknown length");
        malformed(new Proto().number(5, 0x100000000L).bytes(), "uint32 overflow");
        Proto allThreads = new Proto().number(6, 99);
        for (int i = 0; i < 6; i++) allThreads.message(16, entry(i, thread(i, "other", 1)));
        allThreads.message(16, new Proto().number(1, 10).raw(2, new byte[]{0x22, 5, 1}));
        malformed(allThreads.bytes(), "malformed unselected thread still rejected");
        contains(NativeTombstoneSummary.summarize(new byte[2 * 1024 * 1024 + 1]), "exceeds 2 MiB");
        contains(NativeTombstoneSummary.summarize(null), "empty trace");
        contains(NativeTombstoneSummary.summarize(new byte[0]), "empty trace");
    }

    private static void boundedOutputAndFramePriority() {
        Proto top = new Proto().number(6, 777);
        for (int i = 0; i < 20; i++) top.message(16, entry(i, thread(i, "other", 4)));
        top.message(16, entry(777, thread(777, "crash", 45)));
        String result = NativeTombstoneSummary.summarize(top.bytes());
        contains(result, "Crashing thread 777");
        check(occurrences(result, "  #") == 32, "maximum 32 total frames");
        check(!result.contains("Other thread"), "crash gets full frame budget");
        check(!result.contains("#32"), "extra frames omitted");

        String large = repeat("\u4e2d", 1000);
        Proto verbose = new Proto().number(6, 7).text(14, large);
        for (int i = 0; i < 8; i++) verbose.message(15, new Proto().text(1, large));
        Proto thread = new Proto().number(1, 7).text(2, large);
        for (int i = 0; i < 32; i++) thread.message(4,
                new Proto().number(2, i).text(4, large).text(6, large));
        verbose.message(16, entry(7, thread));
        result = NativeTombstoneSummary.summarize(verbose.bytes());
        check(result.getBytes(StandardCharsets.UTF_8).length <= 12 * 1024, "12 KiB UTF-8 output limit");
        contains(result, "[Summary truncated]");
    }

    private static Proto thread(int id, String name, int frameCount) {
        Proto thread = new Proto().number(1, id).text(2, name)
                .message(5, new Proto().text(4, "MEMORY_SECRET"));
        for (int i = 0; i < frameCount; i++) thread.message(4,
                new Proto().number(1, 0x40 + i).number(2, 0x2000 + i)
                        .text(4, "render").number(5, 8).text(6, "/data/libairplay.so"));
        return thread;
    }

    private static Proto entry(int id, Proto value) {
        // Value before key tests unordered map-entry fields too.
        return new Proto().message(2, value).number(1, id);
    }

    private static void malformed(byte[] data, String name) {
        check(NativeTombstoneSummary.summarize(data).contains("malformed protobuf"), name);
    }
    private static void contains(String text, String expected) {
        check(text.contains(expected), "missing: " + expected + " in " + text);
    }
    private static void check(boolean condition, String name) {
        checks++;
        if (!condition) throw new AssertionError(name);
    }
    private static int occurrences(String text, String needle) {
        int count = 0, index = 0;
        while ((index = text.indexOf(needle, index)) >= 0) { count++; index += needle.length(); }
        return count;
    }
    private static String repeat(String text, int count) {
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < count; i++) result.append(text);
        return result.toString();
    }

    private static final class Proto {
        private final ByteArrayOutputStream output = new ByteArrayOutputStream();
        private void varint(long value) {
            while ((value & ~0x7fL) != 0) { output.write((int) (value & 127) | 128); value >>>= 7; }
            output.write((int) value);
        }
        Proto number(int field, long value) { varint((long) field << 3); varint(value); return this; }
        Proto text(int field, String value) { return raw(field, value.getBytes(StandardCharsets.UTF_8)); }
        Proto message(int field, Proto value) { return raw(field, value.bytes()); }
        Proto raw(int field, byte[] value) {
            varint(((long) field << 3) | 2); varint(value.length);
            output.write(value, 0, value.length); return this;
        }
        Proto fixed64(int field) { varint(((long) field << 3) | 1); for (int i=0;i<8;i++) output.write(i); return this; }
        Proto fixed32(int field) { varint(((long) field << 3) | 5); for (int i=0;i<4;i++) output.write(i); return this; }
        byte[] bytes() { return output.toByteArray(); }
    }
}
