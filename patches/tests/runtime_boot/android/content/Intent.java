package android.content; import java.util.*; public class Intent {
 public static final int FLAG_ACTIVITY_CLEAR_TOP=0x04000000,FLAG_ACTIVITY_SINGLE_TOP=0x20000000;
 public final Map<String,Boolean> extras=new HashMap<>(); public String target; public int flags;
 public Intent putExtra(String key,boolean value){extras.put(key,value);return this;}
 public boolean hasExtra(String key){return extras.containsKey(key);}
 public boolean getBooleanExtra(String key,boolean fallback){return extras.getOrDefault(key,fallback);}
 public Intent setClassName(Context context,String name){target=name;return this;}
 public Intent addFlags(int value){flags|=value;return this;}
}
