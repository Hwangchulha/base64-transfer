Base64 Transfer — Android 1.2 (versionCode 3)

Native Java Activity, Android 8.0 / API 26+. No runtime dependencies, network
permission, Google authorization, password storage, or storage permission.
Uses the system SAF file picker. Retains the existing debug signing key.

사용 방법
1. 1 MiB(1,048,576바이트) 미만의 파일을 선택합니다.
2. 파일 전체를 하나의 Base64 JSON 본문으로 변환합니다. 분할하지 않습니다.
3. Gmail로 작성: 작은 본문은 전체 텍스트를 작성 화면에 전달합니다.
   큰 본문은 클립보드를 준비한 뒤 안내 창을 표시합니다. 'Gmail 열기'를
   누르면 제목만 있는 작성 화면이 열립니다. 본문을 길게 눌러 붙여넣기를
   한 번 선택하세요. 본문은 자동 입력되지 않습니다.
4. 텍스트 복사: 전체 텍스트를 한 번 복사합니다. 메일 본문에 붙여넣어
   PC로 보내세요. 복사만으로 PC와 자동 동기화되지 않습니다.
5. 받는 사람과 본문을 확인한 뒤 Gmail에서 직접 보내기를 누르세요.
   이 앱은 실제 전송 여부를 확인하지 못합니다.

중요한 호환성 제한
큰 본문은 텍스트 스트림을 지원하는 수신 앱에서만 붙여넣을 수 있습니다.
실제 Gmail 기기에서 이 경로는 아직 검증하지 못했습니다. 본문 대신 주소만
표시되거나 붙여넣기가 되지 않으면 전송하지 마세요. 지원하지 않는 앱에서의
성공은 보장할 수 없으며, 자동 분할·TXT 첨부·추가 Google 인증으로 우회하지
않습니다. 작은 본문도 Android의 공유 버퍼 상황이나 수신 앱에 따라 실패할
수 있습니다. Base64는 암호화가 아닙니다.

Protocol v2
Input: 0 <= original bytes < 1,048,576. Actual stream reads enforce the limit;
provider size metadata is ignored. At most 1,048,576 bytes are consumed including
the byte proving rejection. Empty input produces one envelope with empty data.
Exactly one JSON string with the same eight fields, in this order:
{"format":"base64-transfer-v2","id":"<full lowercase SHA256>","name":"original.ext","size":123,"sha256":"<full lowercase SHA256>","part":1,"parts":1,"data":"<full original bytes as standard padded Base64>"}

part=1 and parts=1 always. No chunk size, no hidden fragmentation. Both SHA256
and id hash the entire original file. PC must validate the decoded byte count
and SHA256 before saving. Android emits only v2; PC backward compatibility with
v1 is handled separately. SHA256 does not authenticate the sender.

The original filename is capped at 255 UTF-16 code units without splitting a
surrogate pair. Missing/empty name becomes 'unnamed'. Display replaces controls,
bidi formatting and line separators. JSON escapes quotes, backslashes, controls
and surrogates. The original name is NEVER used as a cache filename.

Transport implementation
Small Gmail body: ACTION_SEND, text/plain, EXTRA_TEXT=entire envelope, package
com.google.android.gm. A temporary intent measures the parcel including possible
framework ClipData duplication and chooser nesting. If its serialized size exceeds
800 KiB, the app prepares a URI clipboard, displays a prelaunch paste dialog,
and opens a SUBJECT-ONLY composer. It supplies no EXTRA_TEXT, EXTRA_STREAM,
attachment, or content URI to that composer. Gmail failure offers a chooser.
The user always presses Send; the app never sends mail itself.

Clipboard: a sensitive plain-text ClipData is used when its measured parcel is
<=400 KiB. Above that, or for the large Gmail route, ClipData.newUri references
an app-private text/plain stream. Both modes copy the ENTIRE envelope. Parcel
budgets are application policy, not a guaranteed OS/Gmail/clipboard capacity.
Failures are explained without dumping exception paths or private content.

TextClipboardProvider is exported=false with grantUriPermissions=true. Android's
clipboard grants eligible readers URI access. The provider offers getType,
getStreamTypes, openTypedAssetFile and read-only openFile. It accepts only an exact
content://app.base64transfer.clipboard/text/<canonical lowercase random UUID v4>
URI: no query, fragment, encoding variants, other authorities, path suffixes or
traversal. Only generated files in cache/text-clips are readable. Symlinks,
expired/missing files and non-read modes are rejected with generic errors.
It never exposes an original filesystem path or grants arbitrary-file access.
A recipient can still show the opaque URI instead of consuming text; this app
cannot control another app's paste implementation. Do not send such a result.

Official mechanism and caveat:
https://developer.android.com/develop/ui/views/touch-and-input/copy-paste
The 'Coerce the clipboard data to text' section documents content-URI text stream
coercion. The same page notes apps may ignore URI clips. That is platform mechanism
documentation, not evidence that current Gmail implements this path successfully.

Lifecycle, storage, privacy
One retained native Fragment owns worker conversion, hashing, Base64 generation
and UTF-8 cache writes. Cache files are capped at 1,500,000 bytes each; at most 16
are retained, with 24-hour validity. Old/expired files are pruned when preparing a
new file; Android can evict cache earlier. Clipboard grants cannot bypass expiration.
Re-select the file when a cached clipboard expires. Private files are temporary
clipboard backing, never email attachments. Cache is excluded from Android backup.
Other apps granted clipboard access can read the selected text. Sensitive marking
suppresses previews on supporting systems; it is not access control or encryption.

Rotation retains current conversion; stopped Activities detach listeners. No large
payload is stored in a Bundle. Process death discards the current UI transfer;
private clipboard cache can survive until expiration/eviction. Jobs only hold the
application context. Finishing requests interruption; a provider blocked inside
read/query may delay cancellation until its call returns. Native retained Fragments
are deprecated but still available at the supported API levels.

Build / validate in this workspace
  cd /home/vhehdhkd/work/base64-transfer/android
  ./scripts/build.sh assembleDebug lintDebug
APK: app/build/outputs/apk/debug/app-debug.apk
Build log: build-validation.log
Lint report: app/build/reports/lint-results-debug.txt

The scripts use personal-ledger/.tools/{jdk,sdk,gradle} read-only and a copied
cache in android/.gradle-home. local.properties points to the existing SDK.
Build outputs, temporary files and the preserved debug key stay inside android.
Builds are offline; sandboxed Gradle needs permission for its local daemon socket.
TRANSFER_TOOLS_DIR overrides tools; update local.properties if SDK path changes.
This is a debug-signed APK for testing/manual installation. Nothing is published.

Standalone JVM tests / deterministic interoperability vectors
  ./scripts/test-protocol.sh
  ./scripts/test-protocol.sh vectors 1048575 > build/vector-1048575.jsonl
  python3 tests/verify-vectors.py < build/vector-1048575.jsonl

Generator stdout contains exactly one v2 JSON envelope plus a terminal newline.
Byte i = (i * 31 + 7) & 255. Filename = vector-SIZE.bin. Default SIZE=102401.
SIZE=0 produces empty data; SIZE=1048576 fails. JVM tests cover size boundaries,
short/zero reads, bounded rejection, known hashes, escaping, names, invalid parts,
cancellation, cache roundtrip, URI/traversal/symlink rejection and retention limits.
Independent Python decoding checks schema, exactly one part, bytes, size and SHA256.
Boundary sizes: 0, 1, 2, 3, 102399, 102400, 102401, 1048575; exact 1 MiB rejected.

Validation limitations
No physical-device Gmail, clipboard grant/coerceToText, chooser, TalkBack, rotation
or process-death validation was performed. JVM tests do not prove inter-app grants
or actual Gmail paste behavior. Read build-validation.log for the final build result.
