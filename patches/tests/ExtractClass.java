import jadx.api.JadxArgs;
import jadx.api.JadxDecompiler;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Paths;

/** Extract the real assembled method for host input regression execution. */
public final class ExtractClass {
    public static void main(String[] args) throws Exception {
        JadxArgs options = new JadxArgs();
        options.setInputFile(new File(args[0]));
        options.setSkipResources(true);
        options.setThreadsCount(1);
        options.setInlineMethods(false);
        try (JadxDecompiler decompiler = new JadxDecompiler(options)) {
            decompiler.load();
            String code = decompiler.searchJavaClassByOrigFullName(
                    "com.ideaworks3d.airplay.MultiTouch").getCode();
            Files.write(Paths.get(args[1]), code.getBytes("UTF-8"));
        }
    }
}
