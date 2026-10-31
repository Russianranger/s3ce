package com.ideaworks3d.airplay;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import java.util.*;

/** Actual run() DEX; native execution and Android accessors are modeled boundaries. */
public final class NativeSessionRegression {
    static final Object ENGINE = new Object(), ACTIVITY = new Object(), ROOT = new Object();
    static void check(boolean value, String why) { if (!value) throw new AssertionError(why); }
    static List<String> execute(MethodImplementation code, Throwable failure) throws Throwable {
        Object[] registers = new Object[code.getRegisterCount()];
        registers[registers.length - 1] = ENGINE;
        List<String> stages = new ArrayList<>(); Object result = null;
        for (Instruction instruction : code.getInstructions()) {
            String op = instruction.getOpcode().name;
            if (op.equals("const-string") || op.equals("const-string/jumbo")) {
                registers[((OneRegisterInstruction) instruction).getRegisterA()] =
                        ((StringReference)((ReferenceInstruction)instruction).getReference()).getString();
            } else if (op.equals("const/4")) {
                registers[((OneRegisterInstruction)instruction).getRegisterA()] =
                        ((NarrowLiteralInstruction)instruction).getNarrowLiteral();
            } else if (op.equals("move-result") || op.equals("move-result-object")) {
                registers[((OneRegisterInstruction)instruction).getRegisterA()] = result;
            } else if (op.equals("iget-object") || op.equals("iput-object")) {
                TwoRegisterInstruction fields = (TwoRegisterInstruction) instruction;
                FieldReference field = (FieldReference)((ReferenceInstruction)instruction).getReference();
                check(registers[fields.getRegisterB()] == ENGINE, "field receiver");
                if (op.equals("iput-object")) {
                    check(field.getName().equals("m_Started") && Boolean.TRUE.equals(registers[fields.getRegisterA()]), "started flag");
                } else if (field.getName().equals("m_FileRoot")) registers[fields.getRegisterA()] = ROOT;
                else if (field.getName().equals("m_Airplay")) registers[fields.getRegisterA()] = ACTIVITY;
                else throw new AssertionError("Unexpected field " + field);
            } else if (op.startsWith("invoke-")) {
                FiveRegisterInstruction call = (FiveRegisterInstruction)instruction;
                int[] ids = {call.getRegisterC(),call.getRegisterD(),call.getRegisterE(),call.getRegisterF(),call.getRegisterG()};
                Object[] args = new Object[call.getRegisterCount()];
                for (int i=0;i<args.length;i++) args[i]=registers[ids[i]];
                MethodReference method = (MethodReference)((ReferenceInstruction)instruction).getReference();
                switch (method.getName()) {
                    case "waitForView": check(args[0] == ENGINE, "wait receiver"); stages.add("waitForView"); break;
                    case "valueOf": check(Integer.valueOf(1).equals(args[0]), "start value"); result = Boolean.TRUE; break;
                    case "getAbsolutePath": check(args[0] == ROOT, "root receiver"); result = "/private/data"; break;
                    case "getPackageResourcePath": check(args[0] == ACTIVITY, "activity receiver"); result = "/installed/base.apk"; break;
                    case "getSampleRate": check(args[0] == ENGINE, "rate receiver"); result = 22050; break;
                    case "phase":
                        check(method.getDefiningClass().equals("Lcom/ideaworks3d/thesims3/GameSession;") && op.equals("invoke-static"), "phase target");
                        stages.add((String)args[0]); break;
                    case "runNative":
                        check(op.equals("invoke-direct") && args.length == 4 && args[0] == ENGINE
                                && args[1].equals("/private/data") && args[2].equals("/installed/base.apk")
                                && args[3].equals(22050), "original native arguments/dispatch");
                        stages.add("runNative");
                        if (failure != null) {
                            check(stages.equals(Arrays.asList("waitForView", "Native Main ENTER", "runNative")), "no normal return before native failure");
                            throw failure;
                        }
                        break;
                    case "i": check(args[0].equals("AirplayThread") && args[1].equals("Native code done.  Shutting down"), "original completion log"); break;
                    case "shuttingDown": check(op.equals("invoke-direct") && args[0] == ENGINE && args[1].equals(0), "normal cleanup dispatch"); stages.add("shuttingDown"); break;
                    default: throw new AssertionError("Unexpected call " + method);
                }
            } else if (op.equals("return-void")) return stages;
            else throw new AssertionError("Unexpected opcode " + op);
        }
        throw new AssertionError("No return");
    }
    public static void main(String[] ignored) throws Throwable {
        MethodImplementation code = MultiTouch.findCode("Lcom/ideaworks3d/airplay/AirplayThread;", "run");
        check(code.getRegisterCount() == 4 && code.getTryBlocks().isEmpty(), "original locals/exception path");
        check(execute(code, null).equals(Arrays.asList("waitForView", "Native Main ENTER", "runNative",
                "Native Main RETURN (normal runNative return)", "shuttingDown")), "normal markers and cleanup order");
        Throwable sentinel = new IllegalStateException("native boundary failed");
        try { execute(code, sentinel); throw new AssertionError("failure swallowed"); }
        catch (Throwable actual) { check(actual == sentinel, "same failure propagated"); }
        System.out.println("PASS: actual native-run DEX preserves arguments/locals/cleanup and records ENTER/normal RETURN without swallowing failure.");
    }
}
