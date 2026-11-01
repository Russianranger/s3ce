package android.app; import android.content.*; import android.content.res.*; import android.os.*; import android.view.*; import java.io.*;
 public class Activity extends Context {
 public Intent intent=new Intent(),launched; public View content; public boolean finished;
 public void onCreate(Bundle state){} public Intent getIntent(){return intent;}
 public void setContentView(View view){content=view;} public AssetManager getAssets(){return new AssetManager();}
 public File getFilesDir(){return new File(System.getProperty("s3ce.test.files"));}
 public ClassLoader getClassLoader(){return getClass().getClassLoader();}
 public void startActivity(Intent target){launched=target;} public void finish(){finished=true;}
}
