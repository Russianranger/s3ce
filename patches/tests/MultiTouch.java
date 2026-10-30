package com.ideaworks3d.airplay;

import android.view.MotionEvent;
import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import java.io.File;
import java.util.Arrays;
import java.util.TreeMap;

/** Executes the actual APK touch method's small DEX instruction subset.
 * Unknown instructions fail; this is not an Android/native-runtime emulator. */
final class MultiTouch {
    private static final MethodImplementation CODE = load();
    private static MethodImplementation load() {
        try { return loadDex(); }
        catch (Exception error) { throw new ExceptionInInitializerError(error); }
    }
    private static MethodImplementation loadDex() throws java.io.IOException {
        for (Object item : DexFileFactory.loadDexContainer(new File(
                System.getProperty("s3ce.test.apk")), Opcodes.forApi(26))
                .getEntry("classes.dex").getDexFile().getClasses()) {
            ClassDef klass = (ClassDef) item;
            if (!klass.getType().equals("Lcom/ideaworks3d/airplay/MultiTouch;")) continue;
            for (Object entry : klass.getDirectMethods()) {
                Method method = (Method) entry;
                if (method.getName().equals("onTouchEvent")) return method.getImplementation();
            }
        }
        throw new AssertionError("APK MultiTouch.onTouchEvent missing");
    }
    private static int integer(Object value) { return ((Number) value).intValue(); }
    public static boolean onTouchEvent(AirplayView view, MotionEvent event) {
        TreeMap<Integer,Instruction> instructions = new TreeMap<>();
        int address = 0;
        for (Object item : CODE.getInstructions()) {
            Instruction instruction = (Instruction) item;
            instructions.put(address, instruction);
            address += instruction.getCodeUnits();
        }
        Object[] registers = new Object[CODE.getRegisterCount()];
        Arrays.fill(registers, Integer.valueOf(0));
        registers[registers.length - 2] = view;
        registers[registers.length - 1] = event;
        Object result = null;
        int pc = 0;
        for (int steps = 0; steps < 10000; steps++) {
            Instruction instruction = instructions.get(pc);
            String opcode = instruction.getOpcode().name;
            int next = pc + instruction.getCodeUnits();
            int a = instruction instanceof OneRegisterInstruction
                    ? ((OneRegisterInstruction) instruction).getRegisterA() : -1;
            int b = instruction instanceof TwoRegisterInstruction
                    ? ((TwoRegisterInstruction) instruction).getRegisterB() : -1;
            switch (opcode) {
                case "nop": break;
                case "const/4": case "const/16": case "const":
                    registers[a] = ((NarrowLiteralInstruction) instruction).getNarrowLiteral(); break;
                case "move-result": case "move-result-object": registers[a] = result; break;
                case "move": case "move/from16": case "move-object":
                    registers[a] = registers[b]; break;
                case "float-to-int": registers[a] = integer(registers[b]); break;
                case "add-int/lit8":
                    registers[a] = integer(registers[b])
                            + ((NarrowLiteralInstruction) instruction).getNarrowLiteral(); break;
                case "and-int/lit16":
                    registers[a] = integer(registers[b])
                            & ((NarrowLiteralInstruction) instruction).getNarrowLiteral(); break;
                case "and-int/2addr": registers[a] = integer(registers[a]) & integer(registers[b]); break;
                case "ushr-int/lit8":
                    registers[a] = integer(registers[b])
                            >>> ((NarrowLiteralInstruction) instruction).getNarrowLiteral(); break;
                case "if-eqz": case "if-nez": {
                    boolean zero = integer(registers[a]) == 0;
                    if (zero == opcode.equals("if-eqz")) next = pc + ((OffsetInstruction) instruction).getCodeOffset();
                    break;
                }
                case "if-eq": case "if-ne": case "if-ge": {
                    int left = integer(registers[a]), right = integer(registers[b]);
                    boolean branch = opcode.equals("if-eq") ? left == right
                            : opcode.equals("if-ne") ? left != right : left >= right;
                    if (branch) next = pc + ((OffsetInstruction) instruction).getCodeOffset();
                    break;
                }
                case "goto": case "goto/16": case "goto/32":
                    next = pc + ((OffsetInstruction) instruction).getCodeOffset(); break;
                case "packed-switch": {
                    SwitchPayload payload = (SwitchPayload) instructions.get(
                            pc + ((OffsetInstruction) instruction).getCodeOffset());
                    for (Object entry : payload.getSwitchElements()) {
                        SwitchElement element = (SwitchElement) entry;
                        if (element.getKey() == integer(registers[a])) next = pc + element.getOffset();
                    }
                    break;
                }
                case "invoke-virtual": {
                    FiveRegisterInstruction call = (FiveRegisterInstruction) instruction;
                    int[] args = {call.getRegisterC(), call.getRegisterD(), call.getRegisterE(),
                                  call.getRegisterF(), call.getRegisterG()};
                    MethodReference reference = (MethodReference) ((ReferenceInstruction) instruction).getReference();
                    Object receiver = registers[args[0]];
                    int count = call.getRegisterCount() - 1;
                    Class<?>[] types = new Class<?>[count];
                    Arrays.fill(types, int.class);
                    Object[] values = new Object[count];
                    for (int i = 0; i < count; i++) values[i] = registers[args[i + 1]];
                    try { result = receiver.getClass().getMethod(reference.getName(), types).invoke(receiver, values); }
                    catch (Exception error) { throw new AssertionError("DEX call " + reference, error); }
                    break;
                }
                case "return": return integer(registers[a]) != 0;
                default: throw new AssertionError("Unsupported DEX opcode " + opcode);
            }
            pc = next;
        }
        throw new AssertionError("Touch method did not terminate");
    }
}
