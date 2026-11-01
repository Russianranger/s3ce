package com.ideaworks3d.airplay;

import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import java.util.*;

/** Actual original-bridge DEX; only the Android/bootstrap service boundaries are modeled. */
public final class RuntimeStartupRegression {
    private static final Object ACTIVITY=new Object(), STATE=new Object(), WINDOW=new Object(), SENSOR=new Object();
    private static final String BRIDGE="Lcom/ideaworks3d/airplay/AirplayActivity;";
    private static final String BOOT="Lcom/ideaworks3d/thesims3/GameBootActivity;";
    private static void check(boolean value,String why){if(!value)throw new AssertionError(why);}

    private static List<String> execute(MethodImplementation code,boolean create,boolean prepared){
        Object[] registers=new Object[code.getRegisterCount()];
        Arrays.fill(registers,0);
        registers[registers.length-(create?2:1)]=ACTIVITY;
        if(create)registers[registers.length-1]=STATE;
        Map<Integer,Instruction> instructions=new TreeMap<>();
        int address=0;
        for(Instruction instruction:code.getInstructions()){
            instructions.put(address,instruction);address+=instruction.getCodeUnits();
        }
        List<String> stages=new ArrayList<>();
        Object result=null;
        int pc=0;
        for(int steps=0;steps<500;steps++){
            Instruction instruction=instructions.get(pc);
            check(instruction!=null,"valid control-flow address");
            String op=instruction.getOpcode().name;
            int next=pc+instruction.getCodeUnits();
            int a=instruction instanceof OneRegisterInstruction?((OneRegisterInstruction)instruction).getRegisterA():-1;
            if(op.equals("const-string")||op.equals("const-string/jumbo")){
                registers[a]=((StringReference)((ReferenceInstruction)instruction).getReference()).getString();
            }else if(op.equals("const/4")||op.equals("const/16")){
                registers[a]=((NarrowLiteralInstruction)instruction).getNarrowLiteral();
            }else if(op.equals("new-instance")){
                check(((TypeReference)((ReferenceInstruction)instruction).getReference()).getType()
                        .equals("Ljava/lang/StringBuilder;"),"only original log builder allocated");
                registers[a]=new StringBuilder();
            }else if(op.equals("move-result")||op.equals("move-result-object")){
                registers[a]=result;
            }else if(op.equals("check-cast")){
                check(registers[a]==SENSOR,"original sensor manager cast");
            }else if(op.equals("iput-object")){
                TwoRegisterInstruction fields=(TwoRegisterInstruction)instruction;
                FieldReference field=(FieldReference)((ReferenceInstruction)instruction).getReference();
                check(field.getDefiningClass().equals(BRIDGE)&&field.getName().equals("m_SensorManager")
                        && registers[fields.getRegisterA()]==SENSOR && registers[fields.getRegisterB()]==ACTIVITY,
                        "sensor manager retained before failure path");
                stages.add("sensor-ready");
            }else if(op.equals("if-eqz")){
                check(registers[a] instanceof Integer,"boolean guard consumes helper result");
                if(((Integer)registers[a])==0)next=pc+((OffsetInstruction)instruction).getCodeOffset();
            }else if(op.startsWith("invoke-")){
                FiveRegisterInstruction call=(FiveRegisterInstruction)instruction;
                int[] ids={call.getRegisterC(),call.getRegisterD(),call.getRegisterE(),call.getRegisterF(),call.getRegisterG()};
                Object[] args=new Object[call.getRegisterCount()];
                for(int index=0;index<args.length;index++)args[index]=registers[ids[index]];
                MethodReference method=(MethodReference)((ReferenceInstruction)instruction).getReference();
                String owner=method.getDefiningClass(),name=method.getName();
                if(owner.equals("Ljava/lang/StringBuilder;")){
                    if(name.equals("append")){result=((StringBuilder)args[0]).append(args[1]);}
                    else if(name.equals("toString")){result=args[0].toString();}
                    else check(name.equals("<init>")&&op.equals("invoke-direct"),"original StringBuilder constructor");
                }else if(owner.equals("Landroid/util/Log;")){
                    check(name.equals("i"),"original log operation");
                }else if(owner.equals("Landroid/app/Activity;")){
                    check(op.equals("invoke-super")&&args[0]==ACTIVITY,"mandatory Android superclass receiver");
                    check(name.equals(create?"onCreate":"onStart"),"correct superclass lifecycle");
                    if(create)check(args.length==2&&args[1]==STATE,"original Bundle passed unchanged");
                    stages.add("super");
                }else if(owner.equals("Landroid/view/Window;")){
                    check(name.equals("setFlags")&&args[0]==WINDOW&&args[1].equals(0x400)&&args[2].equals(0x400),
                            "original fullscreen window flags");
                }else if(owner.equals(BOOT)){
                    check(op.equals("invoke-static")&&args.length==1&&args[0]==ACTIVITY,"bootstrap helper receiver");
                    check(method.getParameterTypes().equals(Collections.singletonList("Landroid/app/Activity;"))
                            &&method.getReturnType().equals("Z"),"boolean bootstrap helper ABI");
                    if(create){
                        check(name.equals("prepareMain")&&stages.equals(Arrays.asList("super","sensor-ready")),
                                "bootstrap before view/thread, after mandatory super and safe stop initialization");
                        stages.add("prepare");
                    }else{
                        check(name.equals("canStartMain")&&stages.equals(Collections.singletonList("super")),
                                "per-Activity admission before original native thread construction");
                        stages.add("admit");
                    }
                    result=prepared?1:0;
                }else if(owner.equals(BRIDGE)){
                    check(args[0]==ACTIVITY,"original bridge receiver");
                    switch(name){
                        case "requestWindowFeature":check(args[1].equals(1),"no-title feature");result=1;break;
                        case "getWindow":result=WINDOW;break;
                        case "getRequestedOrientation":result=6;break;
                        case "getSystemService":check(args[1].equals("sensor"),"sensor service");result=SENSOR;break;
                        case "createView":
                            check(prepared&&op.equals("invoke-virtual")&&args[1].equals(0)
                                    &&stages.equals(Arrays.asList("super","sensor-ready","prepare")),
                                    "view created only after successful bootstrap admission");
                            stages.add("view");break;
                        case "startAirplay":
                            check(prepared&&op.equals("invoke-direct")&&stages.equals(Arrays.asList("super","admit")),
                                    "native thread reachable only by successful per-Activity admission");
                            stages.add("thread");break;
                        default:throw new AssertionError("Unexpected original bridge call "+method);
                    }
                }else throw new AssertionError("Unexpected boundary "+method);
            }else if(op.equals("return-void"))return stages;
            else throw new AssertionError("Unexpected opcode "+op);
            pc=next;
        }
        throw new AssertionError("Lifecycle execution did not return");
    }
    public static void main(String[] ignored)throws Exception{
        MethodImplementation create=MultiTouch.findCode(BRIDGE,"onCreate");
        MethodImplementation start=MultiTouch.findCode(BRIDGE,"onStart");
        check(create.getRegisterCount()==6&&start.getRegisterCount()==3,"original local register layout");
        check(create.getTryBlocks().isEmpty()&&start.getTryBlocks().isEmpty(),"no swallowed native/game exception path");
        check(execute(create,true,true).equals(Arrays.asList("super","sensor-ready","prepare","view")),"ready creation path");
        check(execute(create,true,false).equals(Arrays.asList("super","sensor-ready","prepare")),"failed creation has no native view");
        check(execute(start,false,true).equals(Arrays.asList("super","admit","thread")),"ready start path");
        check(execute(start,false,false).equals(Arrays.asList("super","admit")),"failed start has no native thread");
        System.out.println("PASS actual onCreate/onStart DEX: bootstrap and per-Activity admission precede native view/thread; failed startup retains super/sensor cleanup and skips native consumers.");
    }
}
