package app.base64transfer;

import android.app.Fragment;
import android.content.ContentResolver;
import android.content.Context;
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

/** Retained memory-only conversion model. Jobs never capture an Activity. */
@SuppressWarnings("deprecation")
public final class TransferWorker extends Fragment {
    interface Listener { void changed(); }
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private volatile boolean destroyed;
    private Listener listener;
    Transfer transfer;
    boolean busy;
    String message = "파일을 선택해 시작하세요.";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setRetainInstance(true);
    }

    void attach(Listener value) { listener = value; }
    void detach() { listener = null; }

    void load(Context context, Uri uri) {
        Context app = context.getApplicationContext();
        ContentResolver resolver = app.getContentResolver();
        if (busy) return;
        busy = true;
        transfer = null;
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
                status = "파일 전체가 준비됐어요. 클립보드 용량을 확인한 뒤 전달하세요.";
            } catch (IOException | RuntimeException failure) {
                status = "파일을 읽을 수 없습니다 (" + failure.getClass().getSimpleName()
                        + "). 접근 권한과 원본이 1 MiB 미만인지 확인해주세요.";
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
