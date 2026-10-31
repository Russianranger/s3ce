import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import java.io.File;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.locks.ReentrantLock;

/** Runs actual assembled bridge DEX. Android AudioTrack/native generation are
 * explicit host boundaries. Unknown opcodes, fields and full call descriptors
 * fail. The host JVM lock models explicit DEX monitor reentrancy, not ART. */
public final class SoundPlayerRegression {
    static final String PLAYER = "Lcom/ideaworks3d/airplay/SoundPlayer;";
    static final String TRACK = "Landroid/media/AudioTrack;";
    static final boolean ORIGINAL_RACE = Boolean.getBoolean("s3ce.test.originalRace");
    static final Map<String, MethodImplementation> METHODS = load();
    static final Set<String> INVOKED = Collections.synchronizedSet(new TreeSet<>());
    static final String[] TARGETS = {"onPeriodicNotification(" + TRACK + ")V",
        "start()V", "stop()V", "pause()V", "resume()V", "setVolume(I)V"};
    static final Set<String> OPS = Set.of("nop", "const/4", "const/16", "const",
        "const/high16", "const-string", "const-string/jumbo", "move", "move/from16",
        "move/16", "move-object", "move-object/from16", "move-object/16", "move-result",
        "move-result-object", "move-exception", "iget", "iget-object", "iput-object",
        "monitor-enter", "monitor-exit", "if-eqz", "if-nez", "if-eq", "if-ne", "goto",
        "goto/16", "goto/32", "div-int/lit8", "int-to-float", "mul-float/2addr",
        "div-float/2addr", "invoke-direct", "invoke-direct/range", "invoke-virtual",
        "invoke-virtual/range", "invoke-static", "invoke-static/range", "throw", "return-void");
    static final Set<String> CALLS = Set.of(PLAYER+"->init()V", PLAYER+"->generateAudio([SI)V",
        PLAYER+"->start()V", TRACK+"->getPlayState()I", TRACK+"->play()V", TRACK+"->pause()V",
        TRACK+"->stop()V", TRACK+"->flush()V", TRACK+"->release()V",
        TRACK+"->setPlaybackPositionUpdateListener(Landroid/media/AudioTrack$OnPlaybackPositionUpdateListener;)V",
        TRACK+"->setPositionNotificationPeriod(I)I", TRACK+"->write([SII)I",
        TRACK+"->setStereoVolume(FF)I", TRACK+"->getMaxVolume()F",
        "Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I");
    interface Operation { void run() throws Throwable; }
    interface Generator { void run(Player player, short[] data, int count) throws Throwable; }
    static final class Player {
        final ReentrantLock monitor = new ReentrantLock();
        final List<String> events = Collections.synchronizedList(new ArrayList<>());
        Track track;
        short[] samples;
        int bufferSize = 16, period = 4, sampleRate = 48000;
        int generated, nextTrack, initialized;
        Generator generator;
        Throwable initFailure;
        void init() throws Throwable {
            if (initFailure != null) throw initFailure;
            initialized++;
            track = new Track(this, ++nextTrack);
            samples = new short[bufferSize];
            events.add("init:" + track.id);
        }
        void generate(short[] data, int count) throws Throwable {
            check(ORIGINAL_RACE || monitor.isHeldByCurrentThread(), "generate outside SoundPlayer monitor");
            check(data == samples, "wrong native sample array");
            check(count > 0 && count <= samples.length, "wrong native sample count");
            generated++;
            events.add("generate:" + count);
            if (generator != null) generator.run(this, data, count);
        }
    }
    static final class Track {
        final Player player;
        final int id;
        int state = 1; // PLAYSTATE_STOPPED
        boolean released, detached;
        int notificationPeriod = 4, writes, stops, flushes, releases;
        float left, right;
        String failOperation;
        Throwable failure;
        Operation writeHook;
        Track(Player player, int id) { this.player = player; this.id = id; }
        void operation(String name) throws Throwable {
            check(ORIGINAL_RACE || player.monitor.isHeldByCurrentThread(), name + " outside SoundPlayer monitor");
            check(!released, name + " on released AudioTrack");
            player.events.add(name + ":" + id);
            if (name.equals(failOperation)) throw failure;
        }
        Object invoke(String name, Object[] args) throws Throwable {
            operation(name);
            switch (name) {
                case "getPlayState": return state;
                case "play": state = 3; return null;
                case "pause": state = 2; return null;
                case "stop": stops++; state = 1; return null;
                case "flush": flushes++; return null;
                case "release": releases++; released = true; return null;
                case "setPlaybackPositionUpdateListener":
                    check(nil(args[0]), "stop did not detach listener");
                    check(ORIGINAL_RACE || player.track == null, "stop must retire field BEFORE listener detach");
                    detached = true; return null;
                case "setPositionNotificationPeriod":
                    notificationPeriod = integer(args[0]);
                    check(notificationPeriod == 0, "stop did not disable periodic notifications");
                    return 0;
                case "write":
                    check(args[0] == player.samples, "wrong write sample array");
                    check(integer(args[1]) == 0, "wrong sample offset");
                    int count = integer(args[2]);
                    check(count > 0 && count <= player.samples.length, "wrong write count");
                    if (writeHook != null) writeHook.run();
                    check(!released, "write completed after AudioTrack release");
                    writes++; return count;
                case "setStereoVolume":
                    left = floating(args[0]); right = floating(args[1]); return 0;
                default: throw new AssertionError("Unknown host AudioTrack operation " + name);
            }
        }
    }
    static final class Code {
        final MethodImplementation implementation;
        final NavigableMap<Integer, Instruction> instructions = new TreeMap<>();
        Code(MethodImplementation value) {
            implementation = value;
            int pc = 0;
            for (Instruction instruction : value.getInstructions()) {
                instructions.put(pc, instruction); pc += instruction.getCodeUnits();
            }
        }
    }
    static Map<String, MethodImplementation> load() {
        try {
            Map<String, MethodImplementation> result = new HashMap<>();
            var container = DexFileFactory.loadDexContainer(new File(
                    System.getProperty("s3ce.test.apk")), Opcodes.forApi(26));
            for (String entry : container.getDexEntryNames()) {
                for (ClassDef klass : container.getEntry(entry).getDexFile().getClasses()) {
                    if (!PLAYER.equals(klass.getType())) continue;
                    for (Method method : klass.getMethods()) {
                        String signature = signature(method);
                        if (result.put(signature, method.getImplementation()) != null)
                            throw new AssertionError("Duplicate SoundPlayer DEX method " + signature);
                    }
                }
            }
            return result;
        } catch (Exception error) { throw new ExceptionInInitializerError(error); }
    }
    static String signature(MethodReference method) {
        StringBuilder text = new StringBuilder(method.getName()).append('(');
        for (CharSequence type : method.getParameterTypes()) text.append(type);
        return text.append(')').append(method.getReturnType()).toString();
    }
    static String descriptor(MethodReference method) {
        return method.getDefiningClass() + "->" + signature(method);
    }
    static void preflight() {
        // Inspect even branches that a test case may not reach. An unexpected
        // new instruction or call cannot silently become an emulation boundary.
        for(String target:TARGETS)for(Instruction instruction:METHODS.get(target).getInstructions()) {
            check(OPS.contains(instruction.getOpcode().name),"Unknown DEX opcode in "+target+": "+instruction.getOpcode());
            if(instruction instanceof ReferenceInstruction) {
                Reference ref=((ReferenceInstruction)instruction).getReference();
                if(ref instanceof MethodReference)
                    check(CALLS.contains(descriptor((MethodReference)ref)),"Unknown full DEX call "+ref);
                else if(ref instanceof FieldReference) {
                    FieldReference f=(FieldReference)ref;
                    check(PLAYER.equals(f.getDefiningClass()),"Unknown DEX field owner "+f);
                    check(Set.of("m_AudioTrack:"+TRACK,"m_SampleData:[S","m_BufSize:I","m_Period:I","m_SampleRate:I")
                        .contains(f.getName()+':'+f.getType()),"Unknown full DEX field "+f);
                } else check(ref instanceof StringReference,"Unknown DEX reference "+ref);
            }
        }
    }
    static void check(boolean value, String detail) {
        if (!value) throw new AssertionError(detail);
    }
    static int integer(Object value) {
        check(value instanceof Integer, "Expected integer DEX value, got " + value);
        return (Integer) value;
    }
    static float floating(Object value) {
        if (value instanceof Float) return (Float) value;
        if (value instanceof Integer) return Float.intBitsToFloat((Integer) value);
        throw new AssertionError("Expected float DEX value, got " + value);
    }
    static boolean nil(Object value) {
        return value == null || value instanceof Integer && (Integer) value == 0;
    }
    static boolean equal(Object left, Object right) {
        if (nil(left) && nil(right)) return true;
        if (left instanceof Integer && right instanceof Integer) return left.equals(right);
        return left == right;
    }
    static Object object(Object value) { return nil(value) ? null : value; }
    static Object field(Player receiver, FieldReference reference) {
        check(PLAYER.equals(reference.getDefiningClass()), "Wrong field owner " + reference);
        switch (reference.getName() + ':' + reference.getType()) {
            case "m_AudioTrack:" + TRACK: return receiver.track;
            case "m_SampleData:[S": return receiver.samples;
            case "m_BufSize:I": return receiver.bufferSize;
            case "m_Period:I": return receiver.period;
            case "m_SampleRate:I": return receiver.sampleRate;
            default: throw new AssertionError("Unexpected DEX field " + reference);
        }
    }
    static void putField(Player receiver, FieldReference reference, Object value) {
        check(PLAYER.equals(reference.getDefiningClass()), "Wrong field owner " + reference);
        switch (reference.getName() + ':' + reference.getType()) {
            case "m_AudioTrack:" + TRACK:
                receiver.track = (Track) object(value);
                if (receiver.track == null) receiver.events.add("retire");
                return;
            default: throw new AssertionError("Unexpected DEX field store " + reference);
        }
    }
    static int[] argumentRegisters(Instruction instruction) {
        if (instruction instanceof FiveRegisterInstruction) {
            FiveRegisterInstruction call = (FiveRegisterInstruction) instruction;
            return Arrays.copyOf(new int[]{call.getRegisterC(), call.getRegisterD(),
                call.getRegisterE(), call.getRegisterF(), call.getRegisterG()}, call.getRegisterCount());
        }
        if (instruction instanceof RegisterRangeInstruction) {
            RegisterRangeInstruction call = (RegisterRangeInstruction) instruction;
            int[] result = new int[call.getRegisterCount()];
            for (int i = 0; i < result.length; i++) result[i] = call.getStartRegister() + i;
            return result;
        }
        throw new AssertionError("Unsupported invocation register format");
    }
    static Object invoke(Instruction instruction, Object[] registers) throws Throwable {
        MethodReference reference = (MethodReference) ((ReferenceInstruction) instruction).getReference();
        String full = descriptor(reference);
        INVOKED.add(full);
        int[] indexes = argumentRegisters(instruction);
        int wordCount = instruction.getOpcode().name.startsWith("invoke-static") ? 0 : 1;
        for (CharSequence type : reference.getParameterTypes())
            wordCount += type.toString().equals("J") || type.toString().equals("D") ? 2 : 1;
        check(indexes.length == wordCount, "Wrong invocation argument words " + full);
        Object[] args = new Object[indexes.length];
        for (int i = 0; i < args.length; i++) args[i] = registers[indexes[i]];
        switch (full) {
            case PLAYER + "->init()V":
                check(instruction.getOpcode().name.startsWith("invoke-direct"), "init must remain private/direct");
                ((Player) args[0]).init(); return null;
            case PLAYER + "->generateAudio([SI)V":
                check(instruction.getOpcode().name.startsWith("invoke-direct"), "generateAudio must remain private/direct");
                ((Player) args[0]).generate((short[]) args[1], integer(args[2])); return null;
            case PLAYER + "->start()V":
                check(instruction.getOpcode().name.startsWith("invoke-virtual"), "Wrong SoundPlayer start dispatch");
                run((Player) args[0], "start()V"); return null;
            case TRACK + "->getPlayState()I": case TRACK + "->play()V":
            case TRACK + "->pause()V": case TRACK + "->stop()V":
            case TRACK + "->flush()V": case TRACK + "->release()V":
            case TRACK + "->setPlaybackPositionUpdateListener(Landroid/media/AudioTrack$OnPlaybackPositionUpdateListener;)V":
            case TRACK + "->setPositionNotificationPeriod(I)I":
            case TRACK + "->write([SII)I": case TRACK + "->setStereoVolume(FF)I":
                check(instruction.getOpcode().name.startsWith("invoke-virtual"), "Wrong AudioTrack dispatch " + full);
                return ((Track) object(args[0])).invoke(reference.getName(), Arrays.copyOfRange(args, 1, args.length));
            case TRACK + "->getMaxVolume()F":
                check(instruction.getOpcode().name.startsWith("invoke-static"), "Wrong static volume dispatch");
                return 1.0f;
            case "Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I":
                check(instruction.getOpcode().name.startsWith("invoke-static"), "Wrong Log dispatch"); return 0;
            default: throw new AssertionError("Unexpected full DEX call descriptor " + full);
        }
    }
    static int handler(Code code, int pc, Throwable throwable) {
        for (TryBlock<? extends ExceptionHandler> block : code.implementation.getTryBlocks()) {
            if (pc < block.getStartCodeAddress() || pc >= block.getStartCodeAddress() + block.getCodeUnitCount()) continue;
            for (ExceptionHandler handler : block.getExceptionHandlers()) {
                String type = handler.getExceptionType();
                if (type == null || type.equals("Ljava/lang/Throwable;")) return handler.getHandlerCodeAddress();
                throw new AssertionError("Unexpected typed exception handler " + type);
            }
        }
        return -1;
    }
    static void run(Player player, String signature, Object... parameters) throws Throwable {
        MethodImplementation implementation = METHODS.get(signature);
        check(implementation != null, "Actual APK method missing " + signature);
        Code code = new Code(implementation);
        Object[] r = new Object[implementation.getRegisterCount()];
        Arrays.fill(r, Integer.valueOf(0));
        int first = r.length - parameters.length - 1;
        r[first] = player;
        for (int i = 0; i < parameters.length; i++) r[first + i + 1] = parameters[i];
        Object result = null;
        Throwable pending = null;
        int initialHolds = player.monitor.getHoldCount(), pc = 0;
        for (int steps = 0; steps < 10000; steps++) {
            Instruction instruction = code.instructions.get(pc);
            check(instruction != null, "Bad DEX branch target " + pc + " in " + signature);
            String op = instruction.getOpcode().name;
            int next = pc + instruction.getCodeUnits();
            int a = instruction instanceof OneRegisterInstruction ? ((OneRegisterInstruction) instruction).getRegisterA() : -1;
            int b = instruction instanceof TwoRegisterInstruction ? ((TwoRegisterInstruction) instruction).getRegisterB() : -1;
            try {
                switch (op) {
                    case "nop": break;
                    case "const/4": case "const/16": case "const": case "const/high16":
                        r[a] = ((NarrowLiteralInstruction) instruction).getNarrowLiteral(); break;
                    case "const-string": case "const-string/jumbo":
                        r[a] = ((StringReference) ((ReferenceInstruction) instruction).getReference()).getString(); break;
                    case "move": case "move/from16": case "move/16":
                    case "move-object": case "move-object/from16": case "move-object/16": r[a] = r[b]; break;
                    case "move-result": case "move-result-object": r[a] = result; break;
                    case "move-exception": check(pending != null, "move-exception without Throwable"); r[a] = pending; pending = null; break;
                    case "iget": case "iget-object": {
                        FieldReference ref = (FieldReference) ((ReferenceInstruction) instruction).getReference();
                        check(op.equals("iget-object") == (ref.getType().startsWith("L") || ref.getType().startsWith("[")),
                            "Wrong field opcode for " + ref);
                        r[a] = field((Player) object(r[b]), ref); break;
                    }
                    case "iput-object": {
                        FieldReference ref = (FieldReference) ((ReferenceInstruction) instruction).getReference();
                        putField((Player) object(r[b]), ref, r[a]); break;
                    }
                    case "monitor-enter":
                        check(r[a] == player, "Unexpected monitor object"); player.monitor.lock(); break;
                    case "monitor-exit":
                        check(r[a] == player, "Unexpected monitor object"); player.monitor.unlock(); break;
                    case "if-eqz": case "if-nez":
                        if (nil(r[a]) == op.equals("if-eqz")) next = pc + ((OffsetInstruction) instruction).getCodeOffset(); break;
                    case "if-eq": case "if-ne":
                        if (equal(r[a], r[b]) == op.equals("if-eq")) next = pc + ((OffsetInstruction) instruction).getCodeOffset(); break;
                    case "goto": case "goto/16": case "goto/32":
                        next = pc + ((OffsetInstruction) instruction).getCodeOffset(); break;
                    case "div-int/lit8":
                        r[a] = integer(r[b]) / ((NarrowLiteralInstruction) instruction).getNarrowLiteral(); break;
                    case "int-to-float": r[a] = (float) integer(r[b]); break;
                    case "mul-float/2addr": r[a] = floating(r[a]) * floating(r[b]); break;
                    case "div-float/2addr": r[a] = floating(r[a]) / floating(r[b]); break;
                    case "invoke-direct": case "invoke-direct/range":
                    case "invoke-virtual": case "invoke-virtual/range":
                    case "invoke-static": case "invoke-static/range": result = invoke(instruction, r); break;
                    case "throw": throw (Throwable) r[a];
                    case "return-void":
                        check(player.monitor.getHoldCount() == initialHolds, "Monitor leaked on return " + signature); return;
                    default: throw new AssertionError("Unsupported actual SoundPlayer DEX opcode " + op);
                }
            } catch (Throwable throwable) {
                if (throwable instanceof AssertionError) throw throwable;
                int target = handler(code, pc, throwable);
                if (target < 0) {
                    check(player.monitor.getHoldCount() == initialHolds, "Monitor leaked on exception " + signature);
                    throw throwable;
                }
                pending = throwable; next = target;
            }
            pc = next;
        }
        throw new AssertionError("SoundPlayer method did not terminate " + signature);
    }
    static Player ready() throws Throwable {
        Player player = new Player(); player.init(); return player;
    }
    static void unchangedLate(Player player, Track retired) throws Throwable {
        int before = player.generated;
        for (int i = 0; i < 1000; i++) run(player, TARGETS[0], retired);
        check(player.generated == before, "Late queued callback entered native generator");
        check(retired.writes <= 2, "Late queued callback wrote retired AudioTrack");
    }
    static void lifecycle() throws Throwable {
        Player p = ready(); Track first = p.track;
        run(p,"start()V");
        check(p.generated == 1 && first.writes == 1 && first.state == 3, "Start did not prime/play/write");
        check(p.events.indexOf("generate:8") < p.events.indexOf("play:1"), "Start priming order changed");
        run(p,TARGETS[0],first);
        check(p.generated == 2 && first.writes == 2, "Playing callback did not generate/write once");
        check(p.events.contains("generate:4"), "Wrong periodic count");
        run(p,"pause()V"); run(p,TARGETS[0],first);
        check(first.state == 2 && p.generated == 2, "Paused callback generated audio");
        run(p,"resume()V");
        check(p.generated == 3 && first.state == 3 && first.writes == 3, "Resume did not reenter start");
        int beforeNull=p.generated;run(p,TARGETS[0],new Object[]{null});
        check(p.generated==beforeNull,"Null callback track accepted");
        run(p,"setVolume(I)V",25);
        check(first.left == .25f && first.right == .25f, "Original volume formula changed");
        int writes = first.writes;
        run(p,"stop()V");
        check(p.track == null && first.detached && first.notificationPeriod == 0 && first.released
                && first.stops == 1 && first.flushes == 1 && first.releases == 1, "Stop lifecycle incomplete");
        int before = p.generated;
        for (int i=0;i<1000;i++) run(p,TARGETS[0],first);
        check(p.generated == before && first.writes == writes, "Retired callbacks changed native/audio state");
        run(p,"stop()V");run(p,"pause()V");run(p,"resume()V");run(p,"setVolume(I)V",25);
        check(first.releases == 1, "Repeated stop released track twice");
        run(p,"start()V"); Track second = p.track;
        check(second != first && p.initialized == 2 && second.state == 3, "Restart did not initialize replacement");
        before=p.generated;run(p,TARGETS[0],first);
        check(p.generated == before, "Old-track callback accepted after restart");
        run(p,TARGETS[0],second);
        check(p.generated == before+1 && second.writes == 2, "Replacement-track callback not accepted");
        run(p,"stop()V");
    }
    static void reentrantRetirement(boolean restart) throws Throwable {
        Player p=ready();run(p,"start()V");Track first=p.track;int writes=first.writes;
        p.generator=(player,data,count)->{
            player.generator=null;
            run(player,"stop()V");
            if(restart)run(player,"start()V");
        };
        run(p,TARGETS[0],first);
        check(first.released && first.writes==writes,"Reentrant stop wrote released old track");
        check(p.monitor.getHoldCount()==0,"Reentrant monitor remained held");
        if(restart) {
            check(p.track!=first && p.track.writes==1,"Old callback wrote replacement track after reentrant restart");
            run(p,"stop()V");
        }
    }
    static void reentrantPause() throws Throwable {
        Player p=ready();run(p,"start()V");Track track=p.track;int writes=track.writes;
        p.generator=(player,data,count)->{player.generator=null;run(player,"pause()V");};
        run(p,TARGETS[0],track);
        check(track.state==2 && track.writes==writes,"Callback wrote after reentrant pause");
        run(p,"stop()V");
    }
    static void startRetirement(boolean restart) throws Throwable {
        Player p=ready();Track first=p.track;
        p.generator=(player,data,count)->{
            player.generator=null;run(player,"stop()V");
            if(restart)run(player,"start()V");
        };
        run(p,"start()V");
        check(first.released && first.writes==0 && first.state==1,
            "Start played/wrote retired track after reentrant native generation");
        if(restart){check(p.track!=first&&p.track.writes==1,"Start wrote replacement twice");run(p,"stop()V");}
    }
    static void await(CountDownLatch latch,String what) throws Exception {
        check(latch.await(3,TimeUnit.SECONDS),"Timed out waiting for "+what);
    }
    static Thread worker(String name,Operation operation,AtomicReference<Throwable> errors) {
        Thread result=new Thread(()->{try{operation.run();}catch(Throwable t){errors.compareAndSet(null,t);}},name);
        result.setDaemon(true);return result;
    }
    static void concurrentDrain(boolean inWrite) throws Throwable {
        Player p=ready();run(p,"start()V");Track track=p.track;
        CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1),stopStarted=new CountDownLatch(1),stopped=new CountDownLatch(1);
        AtomicReference<Throwable> errors=new AtomicReference<>();
        Operation blocked=()->{entered.countDown();await(release,"callback release");};
        if(inWrite)track.writeHook=blocked;
        else p.generator=(player,data,count)->blocked.run();
        Thread callback=worker("actual-dex-audio-callback",()->run(p,TARGETS[0],track),errors);
        Thread stop=worker("actual-dex-audio-stop",()->{stopStarted.countDown();run(p,"stop()V");stopped.countDown();},errors);
        callback.start();await(entered,"in-flight callback");stop.start();await(stopStarted,"stop attempt");
        try {
            check(!stopped.await(100,TimeUnit.MILLISECONDS),"Stop did not wait for in-flight callback");
            check(!track.released && p.track==track,"Stop released track during native generation/write");
        } finally {release.countDown();}
        callback.join(3000);stop.join(3000);
        check(!callback.isAlive()&&!stop.isAlive(),"SoundPlayer monitor deadlocked");
        if(errors.get()!=null)throw new AssertionError("Concurrent interpreter operation failed",errors.get());
        check(track.released&&track.writes==2,"Callback was not drained before release");
        check(p.events.lastIndexOf("write:1")<p.events.indexOf("retire"),"Release preceded callback write");
        unchangedLate(p,track);
    }
    static void sameFailure(Operation operation,Throwable sentinel) throws Throwable {
        try {operation.run();throw new AssertionError("Expected exception was swallowed");}
        catch(Throwable actual){if(actual!=sentinel)throw new AssertionError("Throwable identity changed",actual);}
    }
    static void exceptionsReleaseMonitors() throws Throwable {
        for(String signature:TARGETS) {
            Player p=ready();Track t=p.track;
            Throwable sentinel=new IllegalStateException("sentinel "+signature);
            if(signature.startsWith("onPeriodic")){t.state=3;p.generator=(player,data,count)->{throw sentinel;};}
            else if(signature.equals("start()V")){p.generator=(player,data,count)->{throw sentinel;};}
            else if(signature.equals("stop()V")){t.failOperation="setPlaybackPositionUpdateListener";t.failure=sentinel;}
            else if(signature.equals("pause()V")){t.state=3;t.failOperation="pause";t.failure=sentinel;}
            else if(signature.equals("resume()V")){t.state=2;p.generator=(player,data,count)->{throw sentinel;};}
            else {t.failOperation="setStereoVolume";t.failure=sentinel;}
            Object[] args=signature.startsWith("onPeriodic")?new Object[]{t}:signature.startsWith("setVolume")?new Object[]{50}:new Object[0];
            sameFailure(()->run(p,signature,args),sentinel);
            check(!p.monitor.isLocked(),"Exception leaked monitor "+signature);
            AtomicReference<Throwable> errors=new AtomicReference<>();
            Thread other=worker("exception-monitor-probe",()->{
                check(p.monitor.tryLock(),"Other thread cannot acquire released monitor");p.monitor.unlock();
            },errors);
            other.start();other.join(3000);check(!other.isAlive(),"Exception-path monitor was not released");
            if(errors.get()!=null)throw new AssertionError("Exception-path monitor probe failed",errors.get());
        }
        Player p=ready();run(p,"stop()V");
        Throwable sentinel=new Error("init failed");p.initFailure=sentinel;
        sameFailure(()->run(p,"start()V"),sentinel);
        check(!p.monitor.isLocked(),"Init exception leaked start monitor");
    }
    public static void main(String[] args) throws Throwable {
        for(String signature:TARGETS)check(METHODS.get(signature)!=null,"Missing exact DEX method "+signature);
        if(ORIGINAL_RACE){
            Player p=ready();Track track=p.track;track.state=3;run(p,"stop()V");
            check(p.track==null&&track.released,"Original stop did not reproduce retired field");
            int before=p.generated;
            try{run(p,TARGETS[0],track);throw new AssertionError("Original callback unexpectedly survived");}
            catch(NullPointerException expected){check(p.generated==before+1,"Original late callback did not enter native generator first");}
            System.out.println("PASS counterexample: actual original DEX late callback enters modeled native generation after stop, then throws null AudioTrack write NPE.");
            return;
        }
        preflight();
        lifecycle();reentrantRetirement(false);reentrantRetirement(true);
        reentrantPause();startRetirement(false);startRetirement(true);
        concurrentDrain(false);concurrentDrain(true);exceptionsReleaseMonitors();
        System.out.println("PASS: actual assembled SoundPlayer DEX covers lifecycle, paused/stale/1000 late callbacks, restart identity, concurrent generation/write drain, reentrant retirement, and exact Throwable/monitor release.");
        System.out.println("Checked "+INVOKED.size()+" full invoked DEX descriptors across six exact method prototypes; unknown bytecode/fields/calls fail.");
    }
}
