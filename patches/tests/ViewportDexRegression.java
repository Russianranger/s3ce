package com.ideaworks3d.airplay;

import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import java.io.File;
import java.util.*;

/** Actual assembled orientation DEX and viewport installation call-path checks.
 * Android Activity/window effects are modeled; platform lifecycle is a separate
 * runtime acceptance boundary. Unknown instructions/calls fail this executor.
 */
public final class ViewportDexRegression {
    static final String THREAD="Lcom/ideaworks3d/airplay/AirplayThread;";
    static final String ACTIVITY="Lcom/ideaworks3d/airplay/AirplayActivity;";
    static final String VIEWPORT="Lcom/ideaworks3d/thesims3/GameViewport;";
    static void check(boolean value,String why){if(!value)throw new AssertionError(why);}
    static final class State { int fixed, original, requested=-999; }
    static Map<String,ClassDef> classes() throws Exception {
        MultiDexContainer<? extends DexFile> container=DexFileFactory.loadDexContainer(
                new File(System.getProperty("s3ce.test.apk")),Opcodes.getDefault());
        Map<String,ClassDef> all=new HashMap<>();
        for(String name:container.getDexEntryNames())for(ClassDef type:container.getEntry(name).getDexFile().getClasses())
            check(all.put(type.getType(),type)==null,"duplicate class");
        return all;
    }
    static Method find(Map<String,ClassDef> classes,String owner,String name){
        ClassDef type=classes.get(owner);check(type!=null,"missing "+owner);
        Method found=null;
        for(Method method:type.getMethods())if(method.getName().equals(name)){
            check(found==null,"ambiguous "+name);found=method;
        }
        check(found!=null&&found.getImplementation()!=null,"missing code "+name);return found;
    }
    static int number(Object value){return((Number)value).intValue();}
    static void orientation(MethodImplementation code,State state,int request){
        TreeMap<Integer,Instruction> ins=new TreeMap<>();int at=0;
        for(Instruction item:code.getInstructions()){ins.put(at,item);at+=item.getCodeUnits();}
        Object[] regs=new Object[code.getRegisterCount()];Arrays.fill(regs,Integer.valueOf(0));
        regs[regs.length-2]=state;regs[regs.length-1]=request;Object result=null;
        int pc=0;
        for(int steps=0;steps<200;steps++){
            Instruction item=ins.get(pc);check(item!=null,"invalid branch");
            String op=item.getOpcode().name;int next=pc+item.getCodeUnits();
            if(op.equals("const/4")||op.equals("const/16")||op.equals("const"))
                regs[((OneRegisterInstruction)item).getRegisterA()]=((NarrowLiteralInstruction)item).getNarrowLiteral();
            else if(op.equals("const-string")||op.equals("const-string/jumbo"))
                regs[((OneRegisterInstruction)item).getRegisterA()]=((StringReference)((ReferenceInstruction)item).getReference()).getString();
            else if(op.equals("new-instance")){
                check(((TypeReference)((ReferenceInstruction)item).getReference()).getType().equals("Ljava/lang/StringBuilder;"),"new type");
                regs[((OneRegisterInstruction)item).getRegisterA()]=new StringBuilder();
            }else if(op.equals("move-result")||op.equals("move-result-object"))regs[((OneRegisterInstruction)item).getRegisterA()]=result;
            else if(op.equals("iget")||op.equals("iget-object")||op.equals("iput")){
                TwoRegisterInstruction field=(TwoRegisterInstruction)item;
                check(regs[field.getRegisterB()]==state,"field owner");
                FieldReference reference=(FieldReference)((ReferenceInstruction)item).getReference();
                switch(reference.getName()){
                    case "m_FixScreenOrientation":
                        if(op.equals("iput"))state.fixed=number(regs[field.getRegisterA()]);
                        else regs[field.getRegisterA()]=state.fixed;break;
                    case "m_OrigScreenOrientation":check(op.equals("iget"),"orig mutation");regs[field.getRegisterA()]=state.original;break;
                    case "m_Airplay":check(op.equals("iget-object"),"activity mutation");regs[field.getRegisterA()]=state;break;
                    default:throw new AssertionError("unexpected field "+reference);
                }
            }else if(op.startsWith("invoke-")){
                FiveRegisterInstruction call=(FiveRegisterInstruction)item;
                int[] ids={call.getRegisterC(),call.getRegisterD(),call.getRegisterE(),call.getRegisterF(),call.getRegisterG()};
                Object[] args=new Object[call.getRegisterCount()];for(int i=0;i<args.length;i++)args[i]=regs[ids[i]];
                MethodReference method=(MethodReference)((ReferenceInstruction)item).getReference();
                if(method.getDefiningClass().equals("Ljava/lang/StringBuilder;")){
                    if(method.getName().equals("append")){((StringBuilder)args[0]).append(args[1]);result=args[0];}
                    else if(method.getName().equals("toString"))result=args[0].toString();
                    else check(method.getName().equals("<init>"),"builder method");
                }else if(method.getDefiningClass().equals("Landroid/util/Log;")){
                    check(method.getName().equals("i"),"log method");result=0;
                }else{
                    check(method.getDefiningClass().equals(ACTIVITY)&&method.getName().equals("setRequestedOrientation")
                            &&args.length==2&&args[0]==state,"orientation target");
                    state.requested=number(args[1]);
                }
            }else if(op.equals("if-ne")){
                TwoRegisterInstruction branch=(TwoRegisterInstruction)item;
                if(number(regs[branch.getRegisterA()])!=number(regs[branch.getRegisterB()]))next=pc+((OffsetInstruction)item).getCodeOffset();
            }else if(op.equals("goto"))next=pc+((OffsetInstruction)item).getCodeOffset();
            else if(op.equals("return-void"))return;
            else throw new AssertionError("Unexpected orientation opcode "+op);
            pc=next;
        }
        throw new AssertionError("orientation did not return");
    }
    public static void main(String[] ignored)throws Exception{
        Map<String,ClassDef> all=classes();
        Method install=find(all,VIEWPORT,"install");
        check(install.getParameterTypes().toString().equals("[Landroid/app/Activity;, Landroid/view/View;]"),"public probe API");
        Method inside=find(all,VIEWPORT,"allInside");
        Set<String> boundsCalls=new HashSet<>();
        for(Instruction item:inside.getImplementation().getInstructions())if(item.getOpcode().name.startsWith("invoke-")){
            MethodReference ref=(MethodReference)((ReferenceInstruction)item).getReference();
            boundsCalls.add(ref.getName());
        }
        check(boundsCalls.containsAll(Arrays.asList("getPointerCount","getX","getY","getHistorySize",
                "getHistoricalX","getHistoricalY")),"candidate lacks complete current/history bounds contract");
        Method layout=find(all,VIEWPORT,"onLayout");
        List<String> layoutCalls=new ArrayList<>();
        for(Instruction item:layout.getImplementation().getInstructions())if(item.getOpcode().name.startsWith("invoke-"))
            layoutCalls.add(((MethodReference)((ReferenceInstruction)item).getReference()).getName());
        check(layoutCalls.contains("getLocationOnScreen")&&layoutCalls.indexOf("cancelGesture")<layoutCalls.indexOf("layout"),
                "cancel must precede relocated child layout");
        Method create=find(all,ACTIVITY,"createView");
        List<String> calls=new ArrayList<>();int installs=0;
        for(Instruction item:create.getImplementation().getInstructions())if(item.getOpcode().name.startsWith("invoke-")){
            MethodReference ref=(MethodReference)((ReferenceInstruction)item).getReference();
            check(!ref.getName().equals("setContentView"),"unwrapped surface installation");
            if(ref.getDefiningClass().equals(VIEWPORT)){
                check(item.getOpcode().name.equals("invoke-static")&&ref.getName().equals("install"),"viewport installation");installs++;
            }
            calls.add(ref.getName());
        }
        check(installs==1&&calls.indexOf("install")<calls.indexOf("attach")
                &&calls.indexOf("attach")<calls.indexOf("setView"),"install/diagnostics/thread ownership order");
        Method fix=find(all,THREAD,"fixOrientation");int cases=0;
        for(int original:new int[]{-1,0,6,8})for(int request:new int[]{Integer.MIN_VALUE,0,1,2,3,Integer.MAX_VALUE}){
            State state=new State();state.original=original;orientation(fix.getImplementation(),state,request);
            check(state.fixed==request,"engine orientation preference changed");
            check(state.requested==(request==1?1:request==2?6:original),"Android orientation mapping");cases++;
        }
        System.out.println("PASS viewport install DEX and "+cases+" original orientation paths; sensor landscape retains engine preference2.");
    }
}
