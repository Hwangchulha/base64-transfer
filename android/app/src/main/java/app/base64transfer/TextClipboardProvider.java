package app.base64transfer;

import android.content.ClipDescription;
import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.res.AssetFileDescriptor;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.ParcelFileDescriptor;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;

/** Only explicitly granted opaque URIs can expose app-generated UTF-8 text. */
public final class TextClipboardProvider extends ContentProvider {
    @Override public boolean onCreate() { return true; }

    private File resolve(Uri uri) throws FileNotFoundException {
        try {
            if (getContext() == null) throw new IOException();
            return ClipboardStore.resolve(getContext().getCacheDir(), uri.toString());
        } catch (IOException | RuntimeException failure) {
            // Never expose filesystem paths or provider exception details.
            throw new FileNotFoundException("Clipboard text unavailable; copy again");
        }
    }

    @Override public String getType(Uri uri) {
        try { resolve(uri); return "text/plain"; }
        catch (FileNotFoundException unavailable) { return null; }
    }

    @Override public String[] getStreamTypes(Uri uri, String filter) {
        return getType(uri) != null && filter != null && ClipDescription.compareMimeTypes("text/plain", filter)
                ? new String[]{"text/plain"} : null;
    }

    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!"r".equals(mode)) throw new FileNotFoundException("Read-only clipboard text");
        return ParcelFileDescriptor.open(resolve(uri), ParcelFileDescriptor.MODE_READ_ONLY);
    }

    @Override public AssetFileDescriptor openTypedAssetFile(Uri uri, String filter, Bundle opts) throws FileNotFoundException {
        if (getStreamTypes(uri, filter) == null) throw new FileNotFoundException("Text stream unavailable");
        return new AssetFileDescriptor(openFile(uri, "r"), 0, AssetFileDescriptor.UNKNOWN_LENGTH);
    }

    @Override public AssetFileDescriptor openTypedAssetFile(Uri uri, String filter, Bundle opts,
                                                           CancellationSignal signal) throws FileNotFoundException {
        if (signal != null) signal.throwIfCanceled();
        return openTypedAssetFile(uri, filter, opts);
    }

    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] args, String order) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException("Read only"); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] args) { throw new UnsupportedOperationException("Read only"); }
    @Override public int delete(Uri uri, String selection, String[] args) { throw new UnsupportedOperationException("Read only"); }
}
