package com.ideaworks3d.thesims3;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Small, bounded reader for Android ApplicationExitInfo native-crash tombstones.
 * Schema: AOSP android-13.0.0_r1, debuggerd/proto/tombstone.proto.
 * https://android.googlesource.com/platform/system/core/+/refs/tags/
 * android-13.0.0_r1/debuggerd/proto/tombstone.proto
 * Thread.registers=3; Register.name=1, u64=2. The crashing thread's general
 * registers are retained. Memory contents, logs, and unknown fields are skipped.
 */
public final class NativeTombstoneSummary {
    private static final int MAX_INPUT = 2 * 1024 * 1024;
    private static final int MAX_OUTPUT = 12 * 1024;
    private static final int MAX_FRAMES = 32;
    private static final int MAX_REGISTERS = 32;
    private static final int MAX_OTHER_THREADS = 3;
    private static final String TRUNCATED = "\n[Summary truncated]\n";

    private NativeTombstoneSummary() { }

    public static String summarize(byte[] data) {
        if (data == null || data.length == 0)
            return "Native tombstone summary unavailable: empty trace.\n";
        if (data.length > MAX_INPUT)
            return "Native tombstone summary unavailable: trace exceeds 2 MiB.\n";
        try {
            Summary summary = readMetadata(data);
            readThreads(data, summary);
            List<Frame> shown = selectedFrames(summary);
            readMappings(data, shown);
            return render(summary, shown);
        } catch (Malformed error) {
            return "Native tombstone summary unavailable: malformed protobuf at byte "
                    + error.offset + " (" + error.getMessage() + ").\n";
        }
    }

    private static Summary readMetadata(byte[] data) throws Malformed {
        Cursor input = new Cursor(data, 0, data.length);
        Summary result = new Summary();
        while (input.more()) {
            int tag = input.tag();
            switch (tag >>> 3) {
                case 4: result.timestamp = input.text(tag, 128); break;
                case 5: result.pid = input.uint32(tag); break;
                case 6: result.tid = input.uint32(tag); break;
                case 10: result.signal = readSignal(input.message(tag)); break;
                case 14: result.abort = input.text(tag, 2048); break;
                case 15:
                    Cursor cause = input.message(tag);
                    String description = "";
                    while (cause.more()) {
                        int field = cause.tag();
                        if (field >>> 3 == 1) description = cause.text(field, 1024);
                        else cause.skip(field);
                    }
                    if (!description.isEmpty() && result.causes.size() < 8)
                        result.causes.add(description);
                    break;
                default: input.skip(tag); break;
            }
        }
        return result;
    }

    private static Signal readSignal(Cursor input) throws Malformed {
        Signal result = new Signal();
        while (input.more()) {
            int tag = input.tag();
            switch (tag >>> 3) {
                case 1: result.number = (int) input.number(tag); break;
                case 2: result.name = input.text(tag, 64); break;
                case 3: result.code = (int) input.number(tag); break;
                case 4: result.codeName = input.text(tag, 64); break;
                case 8: result.hasFault |= input.number(tag) != 0; break;
                case 9:
                    result.fault = input.number(tag);
                    result.hasFault = true;
                    break;
                default: input.skip(tag); break;
            }
        }
        return result;
    }

    private static void readThreads(byte[] data, Summary summary) throws Malformed {
        Cursor input = new Cursor(data, 0, data.length);
        while (input.more()) {
            int tag = input.tag();
            if (tag >>> 3 != 16) { input.skip(tag); continue; }
            Cursor entry = input.message(tag);
            long key = 0;
            Cursor value = null;
            while (entry.more()) {
                int field = entry.tag();
                if (field >>> 3 == 1) key = entry.uint32(field);
                else if (field >>> 3 == 2) value = entry.message(field);
                else entry.skip(field);
            }
            if (value == null) continue;
            boolean crashing = key == summary.tid;
            boolean keep = crashing || summary.others.size() < MAX_OTHER_THREADS;
            ThreadInfo thread = readThread(value, key, keep, crashing);
            if (crashing) summary.crashing = thread;
            else if (keep) summary.others.add(thread);
        }
    }

    private static ThreadInfo readThread(Cursor input, long key, boolean keep, boolean registers) throws Malformed {
        ThreadInfo result = keep ? new ThreadInfo(key) : null;
        while (input.more()) {
            int tag = input.tag();
            switch (tag >>> 3) {
                case 1:
                    long id = input.number(tag);
                    if (result != null) result.id = id & 0xffffffffL;
                    break;
                case 2:
                    if (keep) result.name = input.text(tag, 128);
                    else input.skipAs(tag, 2);
                    break;
                case 3:
                    boolean collectRegister = keep && registers && result.registers.size() < MAX_REGISTERS;
                    Register register = readRegister(input.message(tag), collectRegister);
                    if (collectRegister) result.registers.add(register);
                    break;
                case 4:
                    boolean collect = keep && result.frames.size() < MAX_FRAMES;
                    Frame frame = readFrame(input.message(tag), collect);
                    if (collect) result.frames.add(frame);
                    break;
                default: input.skip(tag); break;
            }
        }
        return result;
    }

    private static Register readRegister(Cursor input, boolean keep) throws Malformed {
        Register result = keep ? new Register() : null;
        while (input.more()) {
            int tag = input.tag();
            switch (tag >>> 3) {
                case 1:
                    if (keep) result.name = input.text(tag, 32);
                    else input.skipAs(tag, 2);
                    break;
                case 2:
                    long value = input.number(tag);
                    if (keep) result.value = value;
                    break;
                default: input.skip(tag); break;
            }
        }
        return result;
    }

    private static Frame readFrame(Cursor input, boolean keep) throws Malformed {
        Frame result = keep ? new Frame() : null;
        while (input.more()) {
            int tag = input.tag();
            switch (tag >>> 3) {
                case 1:
                    long rel = input.number(tag);
                    if (keep) result.relativePc = rel;
                    break;
                case 2:
                    long pc = input.number(tag);
                    if (keep) result.pc = pc;
                    break;
                case 4:
                    if (keep) result.function = input.text(tag, 512);
                    else input.skipAs(tag, 2);
                    break;
                case 5:
                    long offset = input.number(tag);
                    if (keep) result.functionOffset = offset;
                    break;
                case 6:
                    if (keep) result.file = input.text(tag, 512);
                    else input.skipAs(tag, 2);
                    break;
                default: input.skip(tag); break;
            }
        }
        return result;
    }

    private static List<Frame> selectedFrames(Summary summary) {
        List<Frame> result = new ArrayList<>();
        if (summary.crashing != null) addFrames(result, summary.crashing);
        for (ThreadInfo thread : summary.others) addFrames(result, thread);
        return result;
    }

    private static void addFrames(List<Frame> output, ThreadInfo thread) {
        for (Frame frame : thread.frames) {
            if (output.size() == MAX_FRAMES) break;
            output.add(frame);
        }
    }

    private static void readMappings(byte[] data, List<Frame> frames) throws Malformed {
        Cursor input = new Cursor(data, 0, data.length);
        while (input.more()) {
            int tag = input.tag();
            if (tag >>> 3 != 17) { input.skip(tag); continue; }
            Cursor mapping = input.message(tag);
            long begin = 0, end = 0;
            boolean executable = false;
            Cursor name = null;
            while (mapping.more()) {
                int field = mapping.tag();
                switch (field >>> 3) {
                    case 1: begin = mapping.number(field); break;
                    case 2: end = mapping.number(field); break;
                    case 6: executable = mapping.number(field) != 0; break;
                    case 7: name = mapping.message(field); break;
                    default: mapping.skip(field); break;
                }
            }
            if (!executable || Long.compareUnsigned(begin, end) >= 0) continue;
            String label = null;
            for (Frame frame : frames) {
                if (Long.compareUnsigned(frame.pc, begin) < 0
                        || Long.compareUnsigned(frame.pc, end) >= 0) continue;
                if (label == null) label = name == null ? "" : name.remainingText(256);
                frame.mapping = (label.isEmpty() ? "anonymous executable" : label)
                        + " base=" + hex(begin) + " offset=" + hex(frame.pc - begin);
            }
        }
    }

    private static String render(Summary summary, List<Frame> shown) {
        Text output = new Text();
        output.add("Native tombstone (protobuf)\n");
        if (!summary.timestamp.isEmpty()) output.add("Time: " + summary.timestamp + "\n");
        output.add("PID: " + summary.pid + " TID: " + summary.tid + "\n");
        Signal signal = summary.signal;
        if (signal != null) {
            output.add("Signal: " + (signal.name.isEmpty() ? "unknown" : signal.name)
                    + " (" + signal.number + "), "
                    + (signal.codeName.isEmpty() ? "code" : signal.codeName)
                    + " (" + signal.code + ")"
                    + (signal.hasFault ? ", fault=" + hex(signal.fault) : "") + "\n");
        }
        if (!summary.abort.isEmpty()) output.add("Abort: " + summary.abort + "\n");
        for (String cause : summary.causes) output.add("Cause: " + cause + "\n");
        int count = 0;
        if (summary.crashing != null)
            count = renderThread(output, summary.crashing, true, count);
        else output.add("Crashing thread " + summary.tid + " not recorded.\n");
        for (ThreadInfo thread : summary.others) {
            if (count == MAX_FRAMES) break;
            count = renderThread(output, thread, false, count);
        }
        if (shown.isEmpty()) output.add("No backtrace frames recorded.\n");
        return output.finish();
    }

    private static int renderThread(Text output, ThreadInfo thread, boolean crashing, int count) {
        output.add((crashing ? "Crashing thread " : "Other thread ") + thread.id
                + (thread.name.isEmpty() ? "" : " \"" + thread.name + "\"") + ":\n");
        if (!thread.registers.isEmpty()) {
            output.add("  Registers:\n");
            for (int i = 0; i < thread.registers.size(); i++) {
                Register register = thread.registers.get(i);
                output.add((i % 4 == 0 ? "    " : " ")
                        + (register.name.isEmpty() ? "(unnamed)" : register.name)
                        + "=" + hex(register.value)
                        + (i % 4 == 3 || i + 1 == thread.registers.size() ? "\n" : ""));
            }
        }
        int index = 0;
        for (Frame frame : thread.frames) {
            if (count == MAX_FRAMES) break;
            output.add("  #" + (index < 10 ? "0" : "") + index + " pc=" + hex(frame.pc)
                    + " rel_pc=" + hex(frame.relativePc)
                    + (frame.file.isEmpty() ? "" : " " + frame.file)
                    + (frame.function.isEmpty() ? "" : " (" + frame.function
                    + "+" + hex(frame.functionOffset) + ")")
                    + (frame.mapping.isEmpty() ? "" : " [" + frame.mapping + "]") + "\n");
            index++;
            count++;
        }
        return count;
    }

    private static String hex(long value) { return "0x" + Long.toHexString(value); }

    private static final class Summary {
        long pid, tid;
        String timestamp = "", abort = "";
        Signal signal;
        final List<String> causes = new ArrayList<>();
        ThreadInfo crashing;
        final List<ThreadInfo> others = new ArrayList<>();
    }

    private static final class Signal {
        int number, code;
        long fault;
        boolean hasFault;
        String name = "", codeName = "";
    }

    private static final class ThreadInfo {
        long id;
        String name = "";
        final List<Frame> frames = new ArrayList<>();
        final List<Register> registers = new ArrayList<>();
        ThreadInfo(long id) { this.id = id; }
    }

    private static final class Register {
        String name = "";
        long value;
    }

    private static final class Frame {
        long pc, relativePc, functionOffset;
        String function = "", file = "", mapping = "";
    }

    private static final class Malformed extends Exception {
        final int offset;
        Malformed(int offset, String message) { super(message); this.offset = offset; }
    }

    private static final class Cursor {
        final byte[] data;
        final int end;
        int position;
        Cursor(byte[] data, int start, int end) {
            this.data = data; this.position = start; this.end = end;
        }
        boolean more() { return position < end; }
        Malformed bad(String reason) { return new Malformed(position, reason); }
        long varint() throws Malformed {
            long result = 0;
            for (int i = 0; i < 10; i++) {
                if (position == end) throw bad("truncated varint");
                int value = data[position++] & 255;
                if (i == 9 && value > 1) throw bad("varint overflow");
                result |= (long) (value & 127) << (i * 7);
                if (value < 128) return result;
            }
            throw bad("varint overflow");
        }
        int tag() throws Malformed {
            long value = varint();
            if (value == 0 || (value >>> 32) != 0 || (value >>> 3) == 0)
                throw bad("invalid field tag");
            int wire = (int) value & 7;
            if (wire != 0 && wire != 1 && wire != 2 && wire != 5)
                throw bad("unsupported wire type");
            return (int) value;
        }
        void require(int tag, int wire) throws Malformed {
            if ((tag & 7) != wire) throw bad("wrong wire type for known field");
        }
        long number(int tag) throws Malformed { require(tag, 0); return varint(); }
        long uint32(int tag) throws Malformed {
            long value = number(tag);
            if ((value >>> 32) != 0) throw bad("uint32 overflow");
            return value;
        }
        void advance(int size) throws Malformed {
            if (size < 0 || size > end - position) throw bad("truncated field");
            position += size;
        }
        Cursor message(int tag) throws Malformed {
            require(tag, 2);
            long size = varint();
            if (size < 0 || size > end - position) throw bad("invalid length-delimited field");
            int start = position;
            advance((int) size);
            return new Cursor(data, start, position);
        }
        String text(int tag, int cap) throws Malformed { return message(tag).remainingText(cap); }
        String remainingText(int cap) {
            int size = Math.min(end - position, cap);
            String decoded = new String(data, position, size, StandardCharsets.UTF_8);
            StringBuilder clean = new StringBuilder(decoded.length());
            for (int i = 0; i < decoded.length(); i++) {
                char c = decoded.charAt(i);
                clean.append(c < 32 || c == 127 ? ' ' : c);
            }
            if (end - position > cap) clean.append("…");
            return clean.toString();
        }
        void skipAs(int tag, int wire) throws Malformed { require(tag, wire); skip(tag); }
        void skip(int tag) throws Malformed {
            switch (tag & 7) {
                case 0: varint(); break;
                case 1: advance(8); break;
                case 2: message(tag); break;
                case 5: advance(4); break;
                default: throw bad("unsupported wire type");
            }
        }
    }

    private static final class Text {
        final StringBuilder text = new StringBuilder();
        int bytes;
        boolean truncated;
        void add(String value) {
            if (truncated) return;
            int budget = MAX_OUTPUT - TRUNCATED.length();
            for (int i = 0; i < value.length();) {
                int cp = value.codePointAt(i);
                int size = cp < 128 ? 1 : cp < 2048 ? 2 : cp < 65536 ? 3 : 4;
                if (bytes + size > budget) { truncated = true; return; }
                text.appendCodePoint(cp);
                bytes += size;
                i += Character.charCount(cp);
            }
        }
        String finish() { return text.toString() + (truncated ? TRUNCATED : ""); }
    }
}
