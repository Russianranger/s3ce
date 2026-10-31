package com.ideaworks3d.thesims3;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;

/** Read-only grants for generated report files in the independent report process. */
public final class ReportProvider extends ContentProvider {
    private static final String AUTHORITY = "io.github.russianranger.s3ce.reports";
    public static Uri uri(File file) {
        return new Uri.Builder().scheme("content").authority(AUTHORITY)
                .appendPath(file.getName()).build();
    }
    public static File file(File filesDirectory, String name) throws IOException {
        if (name == null || !name.matches("S3CE-diagnostic-[A-Za-z0-9_-]+\\.txt"))
            throw new FileNotFoundException("Unknown report");
        File root = new File(filesDirectory, "reports").getCanonicalFile();
        File result = new File(root, name).getCanonicalFile();
        if (!root.equals(result.getParentFile()) || !result.isFile()) throw new FileNotFoundException("Missing report");
        return result;
    }
    private File resolve(Uri uri) throws FileNotFoundException {
        if (!AUTHORITY.equals(uri.getAuthority()) || uri.getPathSegments().size() != 1)
            throw new FileNotFoundException("Unknown report URI");
        try { return file(getContext().getFilesDir(), uri.getLastPathSegment()); }
        catch (IOException error) { throw new FileNotFoundException(error.getMessage()); }
    }
    @Override public boolean onCreate() { return true; }
    @Override public String getType(Uri uri) { return "text/plain"; }
    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] arguments, String sort) {
        try {
            File report = resolve(uri);
            String[] columns = projection == null ? new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE} : projection;
            MatrixCursor cursor = new MatrixCursor(columns, 1);
            Object[] values = new Object[columns.length];
            for (int i = 0; i < columns.length; i++) {
                if (OpenableColumns.DISPLAY_NAME.equals(columns[i])) values[i] = report.getName();
                if (OpenableColumns.SIZE.equals(columns[i])) values[i] = report.length();
            }
            cursor.addRow(values);
            return cursor;
        } catch (FileNotFoundException error) { throw new IllegalArgumentException(error); }
    }
    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!"r".equals(mode)) throw new FileNotFoundException("Reports are read only");
        return ParcelFileDescriptor.open(resolve(uri), ParcelFileDescriptor.MODE_READ_ONLY);
    }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException(); }
    @Override public int delete(Uri uri, String selection, String[] arguments) { throw new UnsupportedOperationException(); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] arguments) { throw new UnsupportedOperationException(); }
}
