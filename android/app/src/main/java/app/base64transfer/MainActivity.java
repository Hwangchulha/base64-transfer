package app.base64transfer;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.view.Gravity;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Parcel;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

@SuppressWarnings("deprecation")
public final class MainActivity extends Activity implements TransferWorker.Listener {
    private static final int PICK_FILE = 1;
    private TransferWorker worker;
    private TextView detail, fileMeta, status, stateTitle, partLabel;
    private Button pick, gmail, copy;
    private ProgressBar busyIndicator;
    private static final int PARCEL_BUDGET = 800 * 1024;
    private Transfer measuredTransfer;
    private int clipboardBytes = -1;

    @Override public void onCreate(Bundle state) {
        setTheme(R.style.TransferTheme);
        super.onCreate(state);
        worker = (TransferWorker) getFragmentManager().findFragmentByTag("transfer");
        if (worker == null) {
            worker = new TransferWorker();
            getFragmentManager().beginTransaction().add(worker, "transfer").commit();
            getFragmentManager().executePendingTransactions();
        }
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(getColor(R.color.background));
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(24), dp(28), dp(24), dp(32));
        scroll.addView(layout);
        scroll.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                    insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });

        LinearLayout brand = new LinearLayout(this);
        brand.setGravity(Gravity.CENTER_VERTICAL);
        ImageView mark = new ImageView(this);
        mark.setImageResource(R.drawable.ic_transfer);
        mark.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        brand.addView(mark, new LinearLayout.LayoutParams(dp(44), dp(44)));
        TextView wordmark = text(brand, "TEXT TRANSFER", 12, R.color.accent, true);
        wordmark.setLetterSpacing(0.14f);
        wordmark.setPadding(dp(12), 0, 0, 0);
        layout.addView(brand);
        space(layout, 28);
        TextView headline = text(layout, "파일을 텍스트로, 간편하게.", 34, R.color.primary_text, true);
        headline.setLineSpacing(dp(3), 1);
        heading(headline);
        space(layout, 12);
        text(layout, "파일 전체를 한 번에 전달하세요.", 16, R.color.muted_text, false);
        space(layout, 28);

        LinearLayout fileCard = card(layout);
        section(fileCard, "01  파일 선택");
        space(fileCard, 18);
        detail = text(fileCard, "어떤 파일을 보낼까요?", 22, R.color.primary_text, true);
        detail.setTextDirection(View.TEXT_DIRECTION_FIRST_STRONG_LTR);
        space(fileCard, 8);
        fileMeta = text(fileCard, "문서 · 사진 · 모든 파일 형식", 14, R.color.muted_text, false);
        space(fileCard, 20);
        pick = button(fileCard, "파일 선택하기", true, v -> chooseFile());
        space(fileCard, 12);
        text(fileCard, "원본 1 MiB 미만 · 일반 클립보드 한도 800 KiB", 12, R.color.muted_text, false);
        space(layout, 16);

        LinearLayout sendCard = card(layout);
        section(sendCard, "02  텍스트 전달");
        space(sendCard, 16);
        partLabel = text(sendCard, "파일을 선택하면 시작할 수 있어요", 18, R.color.primary_text, true);
        space(sendCard, 20);
        gmail = button(sendCard, "Gmail로 작성", true, v -> compose());
        gmail.setCompoundDrawablesRelativeWithIntrinsicBounds(R.drawable.ic_mail, 0, 0, 0);
        space(sendCard, 10);
        copy = button(sendCard, "텍스트 복사", false, v -> copy());
        copy.setCompoundDrawablesRelativeWithIntrinsicBounds(R.drawable.ic_copy, 0, 0, 0);
        space(sendCard, 14);
        text(sendCard, "파일 전체를 한 번에 전달합니다.\n큰 본문은 Gmail에서 직접 붙여넣도록 안내해 드려요.", 13, R.color.muted_text, false);
        space(layout, 16);

        LinearLayout statusCard = card(layout);
        stateTitle = text(statusCard, "시작할 준비가 됐어요", 15, R.color.accent, true);
        heading(stateTitle);
        busyIndicator = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        busyIndicator.setIndeterminate(true);
        busyIndicator.setIndeterminateTintList(ColorStateList.valueOf(getColor(R.color.accent)));
        busyIndicator.setContentDescription("파일을 읽고 변환하는 중");
        LinearLayout.LayoutParams progressParams = new LinearLayout.LayoutParams(-1, dp(8));
        progressParams.topMargin = dp(12);
        statusCard.addView(busyIndicator, progressParams);
        space(statusCard, 8);
        status = text(statusCard, "", 14, R.color.muted_text, false);
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        space(layout, 16);
        button(layout, "전달 방법 안내", false, v -> new AlertDialog.Builder(this)
                .setTitle("텍스트 전달 안내")
                .setMessage("파일 전체를 한자·한글 모양의 텍스트로 바꿉니다. PC에서 원본 바이트로 복원되며, 먼저 무손실 압축을 시도하며 더 짧을 때만 사용합니다. 암호화는 아닙니다. JPG·XLSX 등 이미 압축된 파일은 효과가 적을 수 있습니다.\n\n약 700 KB 파일은 앱의 일반 클립보드 용량 기준에 들어갑니다. 실제 복사 크기를 표시하며, 한도를 넘으면 나누거나 우회하지 않습니다.\n\n큰 본문은 한 번 복사한 뒤 Gmail 본문을 길게 눌러 붙여넣으세요. 받는 사람과 내용을 확인하고 직접 보내기를 눌러주세요.\n\n일반 텍스트 클립보드이므로 다른 앱에서 읽을 수 있습니다. 키보드 기록 표시 여부는 키보드 앱마다 다르며 보장하지 않습니다. 실제 키보드·Gmail 동작은 아직 검증하지 못했습니다.")
                .setPositiveButton("확인", null).show());
        setContentView(scroll);
        changed();
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private void heading(TextView view) {
        if (Build.VERSION.SDK_INT >= 28) view.setAccessibilityHeading(true);
    }

    private GradientDrawable rounded(int color, int border) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(20));
        if (border != 0) shape.setStroke(dp(1), border);
        return shape;
    }

    private LinearLayout card(LinearLayout parent) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(20), dp(22), dp(20), dp(22));
        card.setBackground(rounded(getColor(R.color.panel), getColor(R.color.outline)));
        parent.addView(card, new LinearLayout.LayoutParams(-1, -2));
        return card;
    }

    private void space(LinearLayout parent, int height) {
        View spacer = new View(this);
        spacer.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        parent.addView(spacer, new LinearLayout.LayoutParams(1, dp(height)));
    }

    private TextView text(LinearLayout parent, String value, int size, int color, boolean bold) {
        TextView text = new TextView(this);
        text.setText(value);
        text.setTextSize(size);
        text.setTextColor(getColor(color));
        text.setTypeface(Typeface.create("sans-serif", bold ? Typeface.BOLD : Typeface.NORMAL));
        text.setLineSpacing(dp(3), 1);
        text.setSaveEnabled(false);
        parent.addView(text, new LinearLayout.LayoutParams(-1, -2));
        return text;
    }

    private void section(LinearLayout parent, String value) {
        TextView title = text(parent, value, 13, R.color.accent, true);
        heading(title);
    }

    private Button button(LinearLayout parent, String value, boolean primary, View.OnClickListener action) {
        Button button = new Button(this);
        button.setText(value);
        button.setTextSize(16);
        button.setAllCaps(false);
        button.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        button.setTextColor(getColor(primary ? R.color.background : R.color.primary_text));
        button.setMinHeight(dp(56));
        button.setMinimumHeight(dp(56));
        button.setPadding(dp(18), dp(14), dp(18), dp(14));
        button.setCompoundDrawablePadding(dp(12));
        button.setBackgroundTintList(null);
        button.setBackground(new RippleDrawable(ColorStateList.valueOf(0x3364e4ce),
                rounded(getColor(primary ? R.color.accent : R.color.secondary_button), 0), null));
        button.setStateListAnimator(null);
        button.setOnClickListener(action);
        parent.addView(button, new LinearLayout.LayoutParams(-1, -2));
        return button;
    }

    private void enabled(Button button, boolean enabled) {
        button.setEnabled(enabled);
        button.setAlpha(enabled ? 1f : 0.38f);
    }

    @Override protected void onStart() { super.onStart(); worker.attach(this); changed(); }
    @Override protected void onStop() { worker.detach(); super.onStop(); }

    @Override public void changed() {
        Transfer transfer = worker.transfer;
        boolean ready = transfer != null && !worker.busy;
        enabled(pick, !worker.busy);
        pick.setText(ready ? "다른 파일 선택" : worker.busy ? "파일을 변환하는 중…" : "파일 선택하기");
        enabled(gmail, ready);
        enabled(copy, ready);
        detail.setText(ready ? Transfer.displayName(transfer.name) : worker.busy ? "잠시만 기다려주세요" : "어떤 파일을 보낼까요?");
        if (ready && measuredTransfer != transfer) {
            measuredTransfer = transfer;
            try { clipboardBytes = parcelBytes(plainClip()); }
            catch (RuntimeException failure) { clipboardBytes = -1; }
        }
        String budget = clipboardBytes < 0 ? "클립보드 크기 확인 불가"
                : "클립보드 " + sizeLabel(clipboardBytes) + " / 800 KiB · "
                + (clipboardBytes <= PARCEL_BUDGET ? "용량 기준 이내" : "복사 한도 초과");
        String compression = ready && transfer.compressed
                ? String.format(java.util.Locale.KOREA, "원본 %,d → 압축 %,d 바이트 · %.1f%% 감소",
                        transfer.size, transfer.packedSize, 100.0 * (transfer.size - transfer.packedSize) / transfer.size)
                : "압축 효과 없음 · 원본 방식";
        fileMeta.setText(ready ? java.text.NumberFormat.getIntegerInstance(java.util.Locale.KOREA).format(transfer.size)
                + " 바이트 · 파일 전체\n" + compression + "\n" + budget : "문서 · 사진 · 모든 파일 형식");
        partLabel.setText(ready ? "파일 전체 · 한 번에 전달"
                : worker.busy ? "전달할 텍스트를 준비하고 있어요" : "파일을 선택하면 시작할 수 있어요");
        partLabel.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        stateTitle.setText(worker.busy ? "변환 중" : ready ? "현재 상태" : "파일 선택 안내");
        busyIndicator.setVisibility(worker.busy ? View.VISIBLE : View.GONE);
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
            worker.load(getApplicationContext(), data.getData());
    }

    private static int parcelBytes(android.os.Parcelable value) {
        Parcel parcel = Parcel.obtain();
        try { value.writeToParcel(parcel, 0); return parcel.dataSize(); }
        finally { parcel.recycle(); }
    }

    private void compose() {
        if (worker.transfer == null || worker.busy) return;
        String body = worker.transfer.envelope(1);
        Intent send = new Intent(Intent.ACTION_SEND).setType("text/plain")
                .putExtra(Intent.EXTRA_SUBJECT, "Text Transfer — 파일 전체")
                .putExtra(Intent.EXTRA_TEXT, body);
        // Include possible framework EXTRA_TEXT -> ClipData duplication and chooser
        // nesting in the measurement, but do not duplicate the actual send Intent.
        Intent measured = new Intent(send).setPackage("com.google.android.gm");
        measured.setClipData(ClipData.newPlainText("파일 전체", body));
        boolean manualPaste;
        try { manualPaste = parcelBytes(Intent.createChooser(measured, "본문 전달")) > PARCEL_BUDGET; }
        catch (RuntimeException failure) {
            message("공유 크기를 확인하지 못했습니다 (" + failure.getClass().getSimpleName() + "). 전체 텍스트 복사를 시도하세요.");
            return;
        }
        if (manualPaste) {
            if (!copyFullText()) return;
            // Subject ONLY: no EXTRA_TEXT, EXTRA_STREAM, URI, or attachment.
            send = new Intent(Intent.ACTION_SEND).setType("text/plain")
                    .putExtra(Intent.EXTRA_SUBJECT, "Text Transfer — 파일 전체");
        }
        if (manualPaste) {
            final Intent subjectOnly = send;
            new AlertDialog.Builder(this)
                    .setTitle("Gmail에서 한 번 붙여넣기")
                    .setMessage("파일 전체를 클립보드에 준비했어요. 다음 Gmail 화면에서 본문을 길게 눌러 ‘붙여넣기’를 한 번 선택하세요. 제목만 열리며 본문은 자동 입력되지 않습니다.\n\n전체 내용은 일반 텍스트로 복사했습니다. 한자·한글 모양이어도 PC에서 원본으로 복원됩니다. 실제 Gmail·키보드 동작은 아직 검증하지 못했습니다. 키보드 기록에 보이지 않으면 본문의 붙여넣기 메뉴를 사용해 보세요.\n\n본문과 받는 사람을 확인한 뒤 직접 보내기를 눌러주세요.")
                    .setPositiveButton("Gmail 열기", (dialog, which) -> launchCompose(subjectOnly, true))
                    .setNegativeButton("취소", null)
                    .show();
            return;
        }
        launchCompose(send, false);
    }

    private void launchCompose(Intent send, boolean manualPaste) {
        send.setPackage("com.google.android.gm");
        String instruction = manualPaste
                ? "전체 텍스트를 클립보드에 준비했습니다. 작성 화면에는 제목만 있습니다. 본문을 길게 눌러 붙여넣기를 한 번 선택하세요. 일반 텍스트로 복사했으며 Gmail 실기기 동작은 미검증입니다. 내용을 확인한 뒤 직접 보내세요."
                : "Gmail에 전체 본문 작성을 요청했습니다. 받는 사람과 본문을 확인하고 직접 보내기를 눌러주세요. 전송 완료는 확인되지 않습니다.";
        try {
            startActivity(send);
            message(instruction);
        } catch (RuntimeException gmailFailure) {
            send.setPackage(null);
            try {
                startActivity(Intent.createChooser(send, "본문 전달"));
                message(manualPaste ? "Gmail을 열지 못했습니다. 다른 앱을 선택한 뒤 본문을 길게 눌러 붙여넣으세요. 제목만 전달됩니다. 전체 본문을 직접 붙여넣으세요."
                        : "Gmail을 열지 못했습니다. 다른 앱에서 전체 본문을 확인하고 직접 보내세요.");
            } catch (RuntimeException shareFailure) {
                message((manualPaste ? "작성 화면을 열지 못했습니다. 전체 텍스트는 클립보드에 있습니다. 메일 앱을 직접 열어 본문에 붙여넣으세요."
                        : "공유 앱을 열지 못했습니다. 전체 텍스트 복사를 시도하세요. 기기에 따라 공유가 실패할 수 있습니다.")
                        + " (" + shareFailure.getClass().getSimpleName() + ")");
            }
        }
    }

    private void copy() { copyFullText(); }

    private static String sizeLabel(int bytes) {
        return String.format(java.util.Locale.KOREA, "%,d 바이트 (%.1f KiB)", bytes, bytes / 1024.0);
    }

    private ClipData plainClip() {
        // Ordinary plain text, deliberately not marked sensitive: preview/history
        // behavior is still up to Android and the user's keyboard application.
        return ClipData.newPlainText("파일 전체", worker.transfer.envelope(1));
    }

    private boolean copyFullText() {
        if (worker.transfer == null || worker.busy) return false;
        ClipboardManager clipboard;
        String body = worker.transfer.envelope(1);
        try {
            clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            if (clipboard == null) throw new IllegalStateException();
            ClipData clip = plainClip();
            int measured = parcelBytes(clip);
            if (measured > PARCEL_BUDGET) {
                message("복사 한도 초과: " + sizeLabel(measured) + " / 800 KiB. 더 작은 원본 파일을 선택해주세요. 복사하거나 분할하지 않았습니다.");
                return false;
            }
            clipboard.setPrimaryClip(clip);
        } catch (RuntimeException failure) {
            message("복사 요청 실패 (" + failure.getClass().getSimpleName()
                    + "). 용량 기준 이내라도 Android 공유 버퍼나 기기 정책으로 실패할 수 있습니다.");
            return false;
        }
        // Read back actual plain text, never coerce a URI or infer success from set().
        try {
            ClipData stored = clipboard.getPrimaryClip();
            CharSequence text = stored != null && stored.getItemCount() > 0 ? stored.getItemAt(0).getText() : null;
            if (text == null || !body.contentEquals(text)) {
                message("복사를 요청했으나 전체 텍스트가 저장되었는지 확인하지 못했습니다. 실제 붙여넣기 결과를 확인해주세요.");
                return false;
            }
        } catch (RuntimeException failure) {
            message("복사를 요청했으나 확인하지 못했습니다 (" + failure.getClass().getSimpleName()
                    + "). 실제 붙여넣기 결과를 확인해주세요.");
            return false;
        }
        message("파일 전체가 일반 텍스트로 복사된 것을 확인했습니다. 메일 본문에 한 번 붙여넣으세요. 키보드 기록 표시는 키보드 앱마다 다릅니다.");
        return true;
    }
}
