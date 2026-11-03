package app.base64transfer;

import android.app.Fragment;
import android.content.ContentResolver;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.OpenableColumns;
import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Retained, memory-only model. Never captures an Activity in a background job. */
@SuppressWarnings("deprecation")
public final class TransferWorker extends Fragment {
    interface Listener { void changed(); }
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private volatile boolean destroyed;
    private Listener listener;
    Transfer transfer;
    int part = 1;
    boolean busy;
    String message = "파일을 선택해 시작하세요.";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setRetainInstance(true);
    }

    void attach(Listener value) { listener = value; }
    void detach() { listener = null; }

    void load(ContentResolver resolver, Uri uri) {
        if (busy) return;
        busy = true;
        transfer = null;
        part = 1;
        message = "파일을 읽고 변환하는 중…";
        changed();
        executor.execute(() -> {
            Transfer result = null;
            String status;
            try {
                String name = "unnamed";
                // Size metadata is deliberately not consulted.
                try (Cursor cursor = resolver.query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
                    if (cursor != null && cursor.moveToFirst()) {
                        int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                        if (index >= 0) name = Transfer.boundedName(cursor.getString(index));
                    }
                } catch (RuntimeException ignored) { /* Missing metadata must not block reading. */ }
                try (InputStream input = resolver.openInputStream(uri)) {
                    if (input == null) throw new IOException("파일 내용을 열 수 없습니다.");
                    result = Transfer.read(input, name);
                }
                status = "준비되었습니다. 전달할 부분을 선택한 뒤 Gmail로 작성하거나 복사하세요.";
            } catch (IOException | RuntimeException failure) {
                status = "파일을 읽을 수 없습니다: " + Transfer.displayName(failure.getMessage());
            }
            final Transfer completed = result;
            final String completedStatus = status;
            if (!destroyed) main.post(() -> {
                if (destroyed) return;
                transfer = completed;
                message = completedStatus;
                busy = false;
                changed();
            });
        });
    }

    private void changed() { if (listener != null) listener.changed(); }

    @Override public void onDestroy() {
        destroyed = true;
        listener = null;
        executor.shutdownNow();
        main.removeCallbacksAndMessages(null);
        transfer = null;
        super.onDestroy();
    }
}
