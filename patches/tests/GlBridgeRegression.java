package com.ideaworks3d.airplay;

import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import java.util.*;

/** Actual compatibility-wrapper bytecode; the original lifecycle is an injected callee. */
public final class GlBridgeRegression {
    private static final class Engine {
        boolean useGl;
        final Object paused = Boolean.FALSE, terminating = Boolean.FALSE;
        final Throwable failure;
        final List<String> stages = new ArrayList<>();
        int calls;
        Throwable recorded;
        Engine(Throwable failure) { this.failure = failure; }
    }
    private static void runBridge(MethodImplementation code, Engine engine, int version) throws Throwable {
        TreeMap<Integer,Instruction> instructions = new TreeMap<>();
        int address = 0;
        for (Instruction instruction : code.getInstructions()) {
            instructions.put(address, instruction);
            address += instruction.getCodeUnits();
        }
        Object[] registers = new Object[code.getRegisterCount()];
        registers[registers.length - 2] = engine;
        registers[registers.length - 1] = version;
        Throwable pending = null;
        int pc = 0;
        for (int steps = 0; steps < 200; steps++) {
            Instruction instruction = instructions.get(pc);
            String opcode = instruction.getOpcode().name;
            int next = pc + instruction.getCodeUnits();
            if (opcode.equals("iget-boolean") || opcode.equals("iget-object")) {
                TwoRegisterInstruction fields = (TwoRegisterInstruction) instruction;
                if (registers[fields.getRegisterB()] != engine) throw new AssertionError("Wrong engine object");
                FieldReference field = (FieldReference) ((ReferenceInstruction) instruction).getReference();
                Object value;
                switch (field.getName()) {
                    case "m_UseGL": value = engine.useGl; break;
                    case "m_Paused": value = engine.paused; break;
                    case "m_Terminating": value = engine.terminating; break;
                    default: throw new AssertionError("Unexpected bridge field " + field);
                }
                registers[fields.getRegisterA()] = value;
            } else if (opcode.equals("invoke-static") || opcode.equals("invoke-direct")) {
                FiveRegisterInstruction call = (FiveRegisterInstruction) instruction;
                int[] args = {call.getRegisterC(), call.getRegisterD(), call.getRegisterE(),
                              call.getRegisterF(), call.getRegisterG()};
                MethodReference method = (MethodReference) ((ReferenceInstruction) instruction).getReference();
                switch (method.getName()) {
                    case "recordGlEntry": case "recordGlExit":
                        if (!Integer.valueOf(version).equals(registers[args[0]])
                                || !Boolean.valueOf(engine.useGl).equals(registers[args[1]])
                                || registers[args[2]] != engine.paused || registers[args[3]] != engine.terminating)
                            throw new AssertionError("Incorrect bridge state arguments");
                        engine.stages.add(method.getName());
                        break;
                    case "recordGlFailure":
                        engine.recorded = (Throwable) registers[args[0]];
                        engine.stages.add(method.getName());
                        break;
                    case "glInit":
                        if (!opcode.equals("invoke-direct") || registers[args[0]] != engine
                                || !Integer.valueOf(version).equals(registers[args[1]]))
                            throw new AssertionError("Original private lifecycle not called directly");
                        engine.calls++;
                        if (engine.failure == null) { engine.useGl = true; break; }
                        boolean handled = false;
                        for (TryBlock<? extends ExceptionHandler> block : code.getTryBlocks()) {
                            if (pc < block.getStartCodeAddress()
                                    || pc >= block.getStartCodeAddress() + block.getCodeUnitCount()) continue;
                            for (ExceptionHandler handler : block.getExceptionHandlers()) {
                                if (!"Ljava/lang/Throwable;".equals(handler.getExceptionType())) continue;
                                next = handler.getHandlerCodeAddress();
                                pending = engine.failure;
                                handled = true;
                                break;
                            }
                        }
                        if (!handled) throw engine.failure;
                        break;
                    default: throw new AssertionError("Unexpected bridge call " + method);
                }
            } else if (opcode.equals("move-exception")) {
                registers[((OneRegisterInstruction) instruction).getRegisterA()] = pending;
            } else if (opcode.equals("throw")) {
                throw (Throwable) registers[((OneRegisterInstruction) instruction).getRegisterA()];
            } else if (opcode.equals("return-void")) return;
            else throw new AssertionError("Unsupported bridge opcode " + opcode);
            pc = next;
        }
        throw new AssertionError("Compatibility bridge did not terminate");
    }
    public static void main(String[] args) throws Throwable {
        MethodImplementation code = MultiTouch.findCode("Lcom/ideaworks3d/airplay/AirplayThread;", "compatGlInit");
        Engine success = new Engine(null);
        runBridge(code, success, 1);
        if (success.calls != 1 || !success.stages.equals(Arrays.asList("recordGlEntry", "recordGlExit")))
            throw new AssertionError("Success bridge stages " + success.stages);
        Throwable sentinel = new IllegalStateException("EGL creation failed");
        Engine failure = new Engine(sentinel);
        try { runBridge(code, failure, 1); throw new AssertionError("Failure was swallowed"); }
        catch (Throwable actual) { if (actual != sentinel) throw new AssertionError("Throwable identity changed", actual); }
        if (failure.calls != 1 || failure.recorded != sentinel
                || !failure.stages.equals(Arrays.asList("recordGlEntry", "recordGlFailure")))
            throw new AssertionError("Failure bridge stages " + failure.stages);
        System.out.println("PASS: actual GL wrapper DEX calls original once, records entry/exit or failure, and rethrows the same Throwable.");
    }
}
