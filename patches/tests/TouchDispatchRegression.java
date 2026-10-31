package com.ideaworks3d.airplay;

import android.view.MotionEvent;
import com.ideaworks3d.thesims3.GameDiagnostics;
import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import java.io.File;
import java.util.*;

/** Executes the APK's actual onTouchEvent wrapper and nested MultiTouch DEX.
 * Unknown instructions or diagnostic method descriptors fail the regression. */
public final class TouchDispatchRegression {
    private static final String VIEW = "Lcom/ideaworks3d/airplay/AirplayView;";
    private static final String EVENT = "Landroid/view/MotionEvent;";
    private static final String DIAGNOSTICS = "Lcom/ideaworks3d/thesims3/GameDiagnostics;";
    private static final MethodImplementation CODE = code();
    private static MethodImplementation code() {
        try { return MultiTouch.findCode(VIEW, "onTouchEvent"); }
        catch (Exception error) { throw new ExceptionInInitializerError(error); }
    }
    private static void descriptor(MethodReference method, String owner, String name,
                                   String result, String... parameters) {
        List<String> actual = new ArrayList<>();
        for (CharSequence parameter : method.getParameterTypes()) actual.add(parameter.toString());
        if (!method.getDefiningClass().equals(owner) || !method.getName().equals(name)
                || !method.getReturnType().equals(result) || !actual.equals(Arrays.asList(parameters)))
            throw new AssertionError("Unexpected APK call descriptor: " + method);
    }
    private static int integer(Object value) { return ((Number) value).intValue(); }
    private static boolean dispatch(AirplayView view, MotionEvent event) {
        TreeMap<Integer, Instruction> instructions = new TreeMap<>();
        int address = 0;
        for (Instruction instruction : CODE.getInstructions()) {
            instructions.put(address, instruction);
            address += instruction.getCodeUnits();
        }
        Object[] registers = new Object[CODE.getRegisterCount()];
        Arrays.fill(registers, Integer.valueOf(0));
        registers[registers.length - 2] = view;
        registers[registers.length - 1] = event;
        Object result = null;
        int pc = 0;
        for (int steps = 0; steps < 100; steps++) {
            Instruction instruction = instructions.get(pc);
            if (instruction == null) throw new AssertionError("Invalid branch target " + pc);
            String opcode = instruction.getOpcode().name;
            int next = pc + instruction.getCodeUnits();
            if (opcode.equals("iget-boolean")) {
                TwoRegisterInstruction field = (TwoRegisterInstruction) instruction;
                FieldReference reference = (FieldReference) ((ReferenceInstruction) instruction).getReference();
                if (registers[field.getRegisterB()] != view || !reference.getDefiningClass().equals(VIEW)
                        || !reference.getName().equals("m_InputTextRunning") || !reference.getType().equals("Z"))
                    throw new AssertionError("Unexpected wrapper field " + reference);
                registers[field.getRegisterA()] = view.m_InputTextRunning ? 1 : 0;
            } else if (opcode.equals("invoke-static") || opcode.equals("invoke-virtual")) {
                FiveRegisterInstruction call = (FiveRegisterInstruction) instruction;
                int a = call.getRegisterC(), b = call.getRegisterD();
                MethodReference method = (MethodReference) ((ReferenceInstruction) instruction).getReference();
                if (method.getDefiningClass().equals(DIAGNOSTICS)) {
                    descriptor(method, DIAGNOSTICS, "touch", "V", EVENT, "Z");
                    if (!opcode.equals("invoke-static") || call.getRegisterCount() != 2
                            || registers[a] != event || integer(registers[b]) != (view.m_InputTextRunning ? 1 : 0))
                        throw new AssertionError("Diagnostic event/gate registers differ from actual view state");
                    GameDiagnostics.touch((MotionEvent) registers[a], integer(registers[b]) != 0);
                } else if (method.getDefiningClass().equals(EVENT)) {
                    descriptor(method, EVENT, "getActionMasked", "I");
                    if (!opcode.equals("invoke-virtual") || call.getRegisterCount() != 1 || registers[a] != event)
                        throw new AssertionError("Wrong MotionEvent receiver");
                    result = event.getActionMasked();
                } else {
                    descriptor(method, "Lcom/ideaworks3d/airplay/MultiTouch;", "onTouchEvent", "Z", VIEW, EVENT);
                    if (!opcode.equals("invoke-static") || call.getRegisterCount() != 2
                            || registers[a] != view || registers[b] != event)
                        throw new AssertionError("Wrong MultiTouch arguments");
                    result = MultiTouch.onTouchEvent(view, event) ? 1 : 0;
                }
            } else if (opcode.equals("move-result")) {
                registers[((OneRegisterInstruction) instruction).getRegisterA()] = result;
            } else if (opcode.equals("const/4")) {
                registers[((OneRegisterInstruction) instruction).getRegisterA()] =
                        ((NarrowLiteralInstruction) instruction).getNarrowLiteral();
            } else if (opcode.equals("if-eqz")) {
                if (integer(registers[((OneRegisterInstruction) instruction).getRegisterA()]) == 0)
                    next = pc + ((OffsetInstruction) instruction).getCodeOffset();
            } else if (opcode.equals("if-eq")) {
                TwoRegisterInstruction branch = (TwoRegisterInstruction) instruction;
                if (integer(registers[branch.getRegisterA()]) == integer(registers[branch.getRegisterB()]))
                    next = pc + ((OffsetInstruction) instruction).getCodeOffset();
            } else if (opcode.equals("return")) {
                return integer(registers[((OneRegisterInstruction) instruction).getRegisterA()]) != 0;
            } else throw new AssertionError("Unsupported touch-wrapper opcode " + opcode);
            pc = next;
        }
        throw new AssertionError("APK touch wrapper did not return");
    }
    private static void verifyProductionHelper() throws Exception {
        MultiDexContainer<? extends DexFile> dex = DexFileFactory.loadDexContainer(
                new File(System.getProperty("s3ce.test.apk")), Opcodes.forApi(26));
        for (String entry : dex.getDexEntryNames()) {
            for (ClassDef klass : dex.getEntry(entry).getDexFile().getClasses()) {
                if (!klass.getType().equals(DIAGNOSTICS)) continue;
                for (Method method : klass.getMethods()) {
                    if (!method.getName().equals("touch") || method.getParameterTypes().size() != 2) continue;
                    descriptor(method, DIAGNOSTICS, "touch", "V", EVENT, "Z");
                    if ((method.getAccessFlags() & 9) != 9 || method.getImplementation() == null)
                        throw new AssertionError("Diagnostic overload must be public static and implemented");
                    return;
                }
            }
        }
        throw new AssertionError("Production two-argument diagnostic helper is missing from APK DEX files");
    }
    public static void main(String[] args) throws Exception {
        verifyProductionHelper();
        AirplayView view = new AirplayView();
        for (int action : new int[]{0, 2, 2, 1}) {
            MotionEvent event = new MotionEvent(action, 0, new int[]{7}, new float[]{100 + action}, new float[]{200});
            int before = GameDiagnostics.events.size();
            if (!dispatch(view, event)) throw new AssertionError("Valid gesture not handled");
            if (GameDiagnostics.events.size() != before + 1
                    || GameDiagnostics.events.get(before) != event || GameDiagnostics.gates.get(before))
                throw new AssertionError("Diagnostic identity/false gate mismatch");
        }
        if (!view.events.equals(Arrays.asList("7:4:100:200", "7:6:102:200", "7:6:102:200", "7:5:101:200")))
            throw new AssertionError("Wrapper changed swipe dispatch: " + view.events);
        view.events.clear();
        view.m_InputTextRunning = true;
        for (int action : new int[]{0, 2, 1}) {
            MotionEvent event = new MotionEvent(action, 0, new int[]{7}, new float[]{100}, new float[]{200});
            if (dispatch(view, event)) throw new AssertionError("Text-gated input unexpectedly handled");
        }
        if (!view.events.isEmpty()) throw new AssertionError("Text-gated input reached native dispatch");
        MotionEvent cancel = new MotionEvent(3, 0, new int[]{3, 11}, new float[]{9, 19}, new float[]{8, 18});
        if (!dispatch(view, cancel) || !view.events.equals(Arrays.asList("3:5:9:8", "11:5:19:18")))
            throw new AssertionError("CANCEL did not release active pointers through text gate");
        if (!GameDiagnostics.gates.equals(Arrays.asList(false, false, false, false, true, true, true, true)))
            throw new AssertionError("Diagnostic gate values changed: " + GameDiagnostics.gates);
        System.out.println("PASS: actual APK touch-wrapper DEX resolves touch(MotionEvent,Z), records the exact event/gate, preserves swipe dispatch, blocks text input, and delivers CANCEL releases.");
    }
}
