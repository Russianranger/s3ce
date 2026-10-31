import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import java.io.File;
import java.util.*;

/** Executes actual surfaceChanged DEX; Android/JNI services are explicit doubles. */
public final class SurfaceMemoryRegression {
    private static final class View {
        final boolean gl;
        int width, height;
        Object bitmap;
        int[] pixels;
        int allocations, nativeCalls, notifications, locks, bitmapBytes;
        View(boolean gl) { this.gl = gl; }
    }
    private static int[] cached;
    private static MethodImplementation code;
    private static final Object ACTIVITY = new Object(), THREAD = new Object(), FORMAT = new Object();
    private static int integer(Object value) { return ((Number)value).intValue(); }
    private static boolean zero(Object value) {
        return value == null || value.equals(Boolean.FALSE) || (value instanceof Number && integer(value) == 0);
    }
    private static void equal(boolean value, String message) { if (!value) throw new AssertionError(message); }
    private static void surface(View view, int width, int height) {
        TreeMap<Integer,Instruction> insns = new TreeMap<>();
        int address = 0;
        for (Instruction instruction : code.getInstructions()) {
            insns.put(address, instruction); address += instruction.getCodeUnits();
        }
        Object[] r = new Object[code.getRegisterCount()];
        int parameters = r.length - 5;
        r[parameters] = view; r[parameters+1] = new Object();
        r[parameters+2] = 4; r[parameters+3] = width; r[parameters+4] = height;
        Object result = null;
        int monitors = 0;
        for (int pc = 0, steps = 0; steps < 1500; steps++) {
            Instruction instruction = insns.get(pc);
            if (instruction == null) throw new AssertionError("Invalid PC " + pc);
            String op = instruction.getOpcode().name;
            int next = pc + instruction.getCodeUnits();
            if (op.equals("const-string") || op.equals("const-string/jumbo")) {
                r[((OneRegisterInstruction)instruction).getRegisterA()] =
                    ((StringReference)((ReferenceInstruction)instruction).getReference()).getString();
            } else if (op.startsWith("const")) {
                r[((OneRegisterInstruction)instruction).getRegisterA()] = ((NarrowLiteralInstruction)instruction).getNarrowLiteral();
            } else if (op.equals("new-instance")) {
                String type = ((TypeReference)((ReferenceInstruction)instruction).getReference()).getType();
                equal(type.equals("Ljava/lang/StringBuilder;"), "Unexpected allocation " + type);
                r[((OneRegisterInstruction)instruction).getRegisterA()] = new StringBuilder();
            } else if (op.startsWith("iget") || op.startsWith("iput")) {
                TwoRegisterInstruction fields = (TwoRegisterInstruction)instruction;
                equal(r[fields.getRegisterB()] == view, "Unexpected field receiver");
                String field = ((FieldReference)((ReferenceInstruction)instruction).getReference()).getName();
                if (op.startsWith("iget")) {
                    Object value;
                    switch (field) {
                        case "m_UseGL": value = view.gl; break;
                        case "m_AirplayActivity": value = ACTIVITY; break;
                        case "m_Width": value = view.width; break;
                        case "m_Height": value = view.height; break;
                        case "m_Pixels": value = view.pixels; break;
                        default: throw new AssertionError("Unexpected read field " + field);
                    }
                    r[fields.getRegisterA()] = value;
                } else {
                    Object value = r[fields.getRegisterA()];
                    switch (field) {
                        case "m_Width": view.width = integer(value); break;
                        case "m_Height": view.height = integer(value); break;
                        case "m_Pixels": view.pixels = (int[])value; break;
                        case "m_FullScreenBitmap": view.bitmap = value; break;
                        default: throw new AssertionError("Unexpected write field " + field);
                    }
                }
            } else if (op.equals("sget-object") || op.equals("sput-object")) {
                String field = ((FieldReference)((ReferenceInstruction)instruction).getReference()).getName();
                int target = ((OneRegisterInstruction)instruction).getRegisterA();
                if (field.equals("g_PixelsLast")) {
                    if (op.equals("sget-object")) r[target] = cached;
                    else cached = (int[])r[target];
                } else {
                    equal(field.equals("RGB_565") && op.equals("sget-object"), "Unexpected static field " + field);
                    r[target] = FORMAT;
                }
            } else if (op.equals("array-length")) {
                TwoRegisterInstruction array = (TwoRegisterInstruction)instruction;
                r[array.getRegisterA()] = ((int[])r[array.getRegisterB()]).length;
            } else if (op.equals("new-array")) {
                TwoRegisterInstruction array = (TwoRegisterInstruction)instruction;
                equal(((TypeReference)((ReferenceInstruction)instruction).getReference()).getType().equals("[I"), "Wrong array type");
                r[array.getRegisterA()] = new int[integer(r[array.getRegisterB()])];
            } else if (op.equals("mul-int/2addr")) {
                TwoRegisterInstruction arithmetic = (TwoRegisterInstruction)instruction;
                r[arithmetic.getRegisterA()] = integer(r[arithmetic.getRegisterA()]) * integer(r[arithmetic.getRegisterB()]);
            } else if (op.startsWith("invoke-")) {
                FiveRegisterInstruction call = (FiveRegisterInstruction)instruction;
                int[] a = {call.getRegisterC(), call.getRegisterD(), call.getRegisterE(), call.getRegisterF(), call.getRegisterG()};
                MethodReference method = (MethodReference)((ReferenceInstruction)instruction).getReference();
                switch (method.getDefiningClass() + "->" + method.getName()) {
                    case "Ljava/lang/StringBuilder;-><init>": break;
                    case "Ljava/lang/StringBuilder;->append": result = ((StringBuilder)r[a[0]]).append(r[a[1]]); break;
                    case "Ljava/lang/StringBuilder;->toString": result = r[a[0]].toString(); break;
                    case "Landroid/util/Log;->i": result = 0; break;
                    case "Lcom/ideaworks3d/airplay/AirplayActivity;->AirplayThread":
                        equal(r[a[0]] == ACTIVITY, "Wrong activity"); result = THREAD; break;
                    case "Lcom/ideaworks3d/airplay/AirplayThread;->lock":
                        equal(r[a[0]] == THREAD && view.locks == 0, "Wrong lock order"); view.locks++; break;
                    case "Lcom/ideaworks3d/airplay/AirplayThread;->unlock":
                        equal(r[a[0]] == THREAD && view.locks == 1, "Wrong unlock order"); view.locks--; break;
                    case "Landroid/graphics/Bitmap;->createBitmap":
                        equal(integer(r[a[0]]) == width && integer(r[a[1]]) == height && r[a[2]] == FORMAT, "Bitmap dimensions/config changed");
                        view.allocations++; view.bitmapBytes += width * height * 2; result = new Object(); break;
                    case "Lcom/ideaworks3d/airplay/AirplayView;->setPixelsNative":
                        equal(r[a[0]] == view && integer(r[a[1]]) == width && integer(r[a[2]]) == height
                            && r[a[3]] == view.pixels && view.pixels.length == width * height && view.locks == 1,
                            "Native pixel/dimension protocol changed"); view.nativeCalls++; break;
                    case "Ljava/lang/Object;->notify":
                        equal(r[a[0]] == view && monitors == 1 && view.locks == 0, "Notify ordering changed");
                        view.notifications++; break;
                    default: throw new AssertionError("Unexpected call " + method);
                }
            } else if (op.equals("move-result") || op.equals("move-result-object")) {
                r[((OneRegisterInstruction)instruction).getRegisterA()] = result;
            } else if (op.equals("monitor-enter")) {
                equal(r[((OneRegisterInstruction)instruction).getRegisterA()] == view && monitors == 0, "Monitor ownership"); monitors++;
            } else if (op.equals("monitor-exit")) { equal(monitors == 1, "Monitor exit"); monitors--;
            } else if (op.equals("if-eqz") || op.equals("if-nez")) {
                boolean isZero = zero(r[((OneRegisterInstruction)instruction).getRegisterA()]);
                if (op.equals("if-eqz") == isZero) next = pc + ((OffsetInstruction)instruction).getCodeOffset();
            } else if (op.equals("if-eq") || op.equals("if-ne")) {
                TwoRegisterInstruction compare = (TwoRegisterInstruction)instruction;
                boolean same = Objects.equals(r[compare.getRegisterA()], r[compare.getRegisterB()]);
                if (op.equals("if-eq") == same) next = pc + ((OffsetInstruction)instruction).getCodeOffset();
            } else if (op.equals("goto") || op.equals("goto/16") || op.equals("goto/32")) {
                next = pc + ((OffsetInstruction)instruction).getCodeOffset();
            } else if (op.equals("return-void")) {
                equal(monitors == 0 && view.locks == 0, "Unreleased monitor/native lock"); return;
            } else throw new AssertionError("Unsupported surface opcode " + op);
            pc = next;
        }
        throw new AssertionError("surfaceChanged did not terminate");
    }
    public static void main(String[] args) throws Exception {
        var container = DexFileFactory.loadDexContainer(new File(System.getProperty("s3ce.test.apk")), Opcodes.getDefault());
        for (String name : container.getDexEntryNames()) for (ClassDef type : container.getEntry(name).getDexFile().getClasses())
            if (type.getType().equals("Lcom/ideaworks3d/airplay/AirplayView;")) for (Method method : type.getMethods())
                if (method.getName().equals("surfaceChanged")) code = method.getImplementation();
        equal(code != null, "No actual surfaceChanged DEX");
        boolean original = Boolean.getBoolean("s3ce.test.originalBitmap");
        cached = null;
        View gl = new View(true);
        surface(gl, 1920, 1080); surface(gl, 1920, 1080); surface(gl, 2160, 1080);
        equal(gl.allocations == (original ? 3 : 0), "Unexpected GL bitmap allocation count " + gl.allocations);
        equal(gl.nativeCalls == 3 && gl.notifications == 3 && gl.pixels.length == 2160*1080, "GL protocol changed");
        cached = null;
        View software = new View(false);
        surface(software, 1920, 1080); int[] first = software.pixels;
        surface(software, 1920, 1080);
        equal(software.pixels == first, "Software array reuse changed");
        surface(software, 960, 640);
        equal(software.allocations == 3 && software.bitmap != null && software.pixels.length == 960*640, "Software allocation changed");
        View reuse = new View(false); surface(reuse, 960, 640);
        equal(reuse.pixels == software.pixels && reuse.allocations == 1, "Static array reuse changed");
        System.out.println("PASS: actual surfaceChanged DEX: GL bitmap allocations=" + gl.allocations
            + "; software allocations, pixel arrays, JNI dimensions and lock/notify ordering preserved."
            + (original ? " Original GL counterexample retained." : " Avoids 4,147,200 CPU bytes at 1920x1080; Android/EGL/native services are doubles."));
    }
}
