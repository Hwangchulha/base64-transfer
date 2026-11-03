package app.base64transfer;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipDescription;
import android.content.ClipboardManager;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Parcel;
import android.os.PersistableBundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

@SuppressWarnings("deprecation")
public final class MainActivity extends Activity implements TransferWorker.Listener {
    private static final int PICK_FILE = 1;
    private TransferWorker worker;
    private TextView detail;
    private TextView status;
    private Button pick, previous, next, gmail, copy;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        worker = (TransferWorker) getFragmentManager().findFragmentByTag("transfer");
        if (worker == null) {
            worker = new TransferWorker();
            getFragmentManager().beginTransaction().add(worker, "transfer").commit();
            getFragmentManager().executePendingTransactions();
        }
        ScrollView scroll = new ScrollView(this);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        int padding = (int) (20 * getResources().getDisplayMetrics().density);
        layout.setPadding(padding, padding, padding, padding);
        scroll.addView(layout);
        // Honor system bars on Android 15's edge-to-edge layout.
        scroll.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                    insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });
        label(layout, "파일을 텍스트로 보내기", 26);
        label(layout, "1 MiB(1,048,576바이트) 미만의 파일을 선택하세요. 원본을 100 KiB씩 나누어 최대 11개 부분으로 변환합니다. 이 크기는 앱의 설계 기준이며, 기기에 따라 공유나 복사가 실패할 수 있습니다.", 16);
        label(layout, "각 부분을 Gmail이나 복사로 전달하세요. Gmail에서 직접 보내기를 눌러야 합니다. 보낸 뒤 다음 부분으로 이동하세요. 전송 여부는 이 앱에서 확인할 수 없습니다. Base64 변환은 암호화가 아닙니다.", 16);
        pick = button(layout, "파일 선택", v -> chooseFile());
        detail = label(layout, "", 18);
        previous = button(layout, "이전 부분", v -> { worker.part--; changed(); });
        next = button(layout, "다음 부분", v -> { worker.part++; changed(); });
        gmail = button(layout, "Gmail로 작성", v -> compose());
        copy = button(layout, "선택한 부분 복사", v -> copy());
        status = label(layout, "", 16);
        setContentView(scroll);
        changed();
    }

    private TextView label(LinearLayout parent, String value, int size) {
        TextView text = new TextView(this);
        text.setText(value);
        text.setTextSize(size);
        text.setPadding(0, 10, 0, 10);
        text.setSaveEnabled(false);
        parent.addView(text);
        return text;
    }

    private Button button(LinearLayout parent, String value, View.OnClickListener action) {
        Button button = new Button(this);
        button.setText(value);
        button.setOnClickListener(action);
        parent.addView(button);
        return button;
    }

    @Override protected void onStart() { super.onStart(); worker.attach(this); changed(); }
    @Override protected void onStop() { worker.detach(); super.onStop(); }

    @Override public void changed() {
        Transfer transfer = worker.transfer;
        boolean ready = transfer != null && !worker.busy;
        pick.setEnabled(!worker.busy);
        previous.setEnabled(ready && worker.part > 1);
        next.setEnabled(ready && worker.part < transfer.parts);
        gmail.setEnabled(ready);
        copy.setEnabled(ready);
        detail.setText(ready ? Transfer.displayName(transfer.name) + "\n" + transfer.size
                + "바이트 · 부분 " + worker.part + " / " + transfer.parts : "변환한 파일이 없습니다");
        status.setText(worker.message);
    }

    private void message(String value) { worker.message = value; changed(); }

    private void chooseFile() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*")
                .addCategory(Intent.CATEGORY_OPENABLE)
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try { startActivityForResult(intent, PICK_FILE); }
        catch (RuntimeException failure) { message("파일 선택기를 열 수 없거나 접근이 거부되었습니다."); }
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == PICK_FILE && result == RESULT_OK && data != null && data.getData() != null)
            worker.load(getApplicationContext().getContentResolver(), data.getData());
    }

    private void compose() {
        if (worker.transfer == null) return;
        String body = worker.transfer.envelope(worker.part);
        Intent send = new Intent(Intent.ACTION_SEND).setType("text/plain")
                .putExtra(Intent.EXTRA_SUBJECT, "Base64 Transfer — part " + worker.part + " / " + worker.transfer.parts)
                .putExtra(Intent.EXTRA_TEXT, body);
        // Framework may migrate EXTRA_TEXT to ClipData. Measure that duplicated
        // form, including chooser nesting, without duplicating the actual send Intent.
        Intent measured = new Intent(send).setPackage("com.google.android.gm");
        measured.setClipData(ClipData.newPlainText("Base64 part", body));
        Parcel parcel = Parcel.obtain();
        try {
            Intent.createChooser(measured, "선택한 부분 보내기").writeToParcel(parcel, 0);
            if (parcel.dataSize() >= 900 * 1024) {
                message("이 기기에서 공유하기에는 내용이 너무 큽니다.");
                return;
            }
        } finally { parcel.recycle(); }
        send.setPackage("com.google.android.gm");
        try {
            startActivity(send);
            message("Gmail 작성 화면을 열었습니다. Gmail에서 보내기를 눌러주세요. 현재 부분은 그대로 선택되어 있으며 전송 여부는 확인되지 않습니다.");
        } catch (RuntimeException gmailFailure) {
            send.setPackage(null);
            try {
                startActivity(Intent.createChooser(send, "선택한 부분 보내기"));
                message("Gmail을 열지 못했습니다. 다른 앱을 선택해 직접 보내주세요. 현재 부분은 그대로 선택됩니다.");
            } catch (RuntimeException shareFailure) {
                message("공유 앱을 열지 못했습니다. 기기에서 이 크기의 공유를 거부할 수 있습니다. 선택한 부분 복사를 시도하세요.");
            }
        }
    }

    private void copy() {
        if (worker.transfer == null) return;
        try {
            ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            if (clipboard == null) throw new IllegalStateException("Clipboard unavailable");
            ClipData clip = ClipData.newPlainText("Base64 part", worker.transfer.envelope(worker.part));
            PersistableBundle extras = new PersistableBundle();
            extras.putBoolean(Build.VERSION.SDK_INT >= 33 ? ClipDescription.EXTRA_IS_SENSITIVE
                    : "android.content.extra.IS_SENSITIVE", true);
            clip.getDescription().setExtras(extras);
            clipboard.setPrimaryClip(clip);
            message("선택한 부분을 복사했습니다. 메일·메신저 등 전달할 앱에 붙여넣어 PC로 보내주세요. 복사만으로 PC에 전달되지는 않습니다. 다른 앱에서 클립보드에 접근할 수 있습니다.");
        } catch (RuntimeException failure) {
            message("클립보드 복사에 실패했습니다. 설계 크기 이내라도 기기나 클립보드 서비스에서 거부할 수 있습니다. Gmail로 작성을 시도하세요.");
        }
    }
}
