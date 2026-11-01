package android.app;
import android.view.View;
import android.view.Window;
import java.io.File;
public final class Activity {
    public View content;
    private final Window window=new Window();
    private final File files;
    public Activity(File directory) { files=directory; }
    public Window getWindow() { return window; }
    public File getFilesDir() { return files; }
    public void setContentView(View value) {
        if(content!=null && content!=value) content.testDetach();
        content=value;
    }
}
