Text Transfer — Android 1.4.0 (versionCode 5)

Native Java Activity, Android 8.0 / API 26+. No additional runtime dependencies,
network permission, Google authorization, password storage or storage permission.
Uses the SAF file picker and the existing debug signing key.

사용 방법
1. 1 MiB(1,048,576바이트) 미만의 파일을 선택합니다.
2. 파일 전체를 한자·한글 모양의 텍스트 하나로 변환합니다. PC에서 원본
   바이트로 복원됩니다. 먼저 zlib 무손실 압축을 시도하고 전체 JSON이 더 짧을
   때만 압축 결과를 사용합니다. 암호화가 아니며 분할하지 않습니다.
   파일 카드에 원본 → 압축 크기와 감소율을 표시하고, 효과가 없으면
   ‘압축 효과 없음 · 원본 방식’으로 표시합니다.
3. 파일 카드에서 실제 클립보드 크기와 800 KiB 한도를 확인합니다.
   약 700 KB~700 KiB 원본은 이 용량 기준에 들어갑니다. 실제 크기를 검사하므로
   모든 1 MiB 미만 파일이 복사 가능한 것은 아닙니다.
4. '텍스트 복사'는 전체 JSON을 일반 텍스트 클립보드에 넣습니다. 다시 읽은
   getText()가 본문과 정확히 같을 때만 복사 확인을 표시합니다. 다시 읽기
   실패 시 복사 요청은 했지만 확인하지 못했다고 표시합니다.
5. Gmail로 작성: 작은 본문은 전체 텍스트를 작성 화면으로 전달합니다.
   큰 본문은 일반 텍스트 복사·읽기 확인 후 사전 안내 창을 표시합니다.
   'Gmail 열기'를 누르면 제목만 있는 화면이 열립니다. 본문을 길게 눌러
   붙여넣기를 한 번 선택하세요. 본문이 자동 입력되는 것은 아닙니다.
6. 본문과 받는 사람을 확인한 뒤 직접 보내기를 눌러주세요.

일반 클립보드와 실제 기기 제한
URI 클립보드, content provider, 파일 첨부, 자동 분할은 사용하지 않습니다.
일반 텍스트를 민감 정보로 표시하지 않으므로 다른 앱에서 읽을 수 있습니다.
키보드 기록에 표시·저장할지는 키보드 앱 자체 정책이며 보장하지 않습니다.
클립보드 저장 후 확인 성공도 키보드 기록 표시나 Gmail 전송 성공을 의미하지
않습니다. 실제 키보드·Gmail 기기 동작은 아직 검증하지 못했습니다.
용량 기준 이내라도 Android의 공유 Binder 버퍼 상황에 따라 실패할 수 있습니다.
예외 시 경로·본문 대신 짧은 오류 클래스와 작업 결과를 표시합니다.

Protocol selection: v4 compressed / v3 original
Input: 0 <= original bytes < 1,048,576. Bounded actual reads enforce the limit;
provider size metadata is ignored. The read proving rejection consumes at most
1,048,576 bytes. Empty input produces one envelope with empty data.
Always exactly one JSON string. First produce RFC1950 zlib-wrapped bytes using
Deflater(DEFAULT_COMPRESSION, nowrap=false); Deflater.end() runs in finally.
Compression, encoding and candidate selection run inside the existing conversion
worker. Build both full JSON candidates and select v4 ONLY if its Java String
length is strictly smaller than v3. Ties keep v3. No lossy conversion, extraction,
file splitting or encryption. No new dependencies or network access.

v3 fallback, unchanged eight-field schema:
{"format":"text-transfer-v3","id":"<original lowercase SHA256>","name":"original.ext","size":123,"sha256":"<original lowercase SHA256>","part":1,"parts":1,"data":"<original bytes compact15>"}

v4, same eight fields plus encoding and packedSize:
{"format":"text-transfer-v4","id":"<original lowercase SHA256>","name":"original.ext","size":123,"sha256":"<original lowercase SHA256>","part":1,"parts":1,"encoding":"zlib","packedSize":42,"data":"<zlib bytes compact15>"}

size, id and sha256 ALWAYS describe the original file, not compressed bytes.
packedSize is the compressed byte count. part=1 and parts=1 for both formats.
Public Transfer.compressed identifies the selected format. Transfer.packedSize
is compressed bytes for v4, original bytes for v3 (v3 JSON has no packedSize).
PC must decode compact15 using packedSize for v4, then decompress zlib with strict
output bounds, EOF and no trailing junk, and validate original size and SHA256.
Compression benefit depends on content: text/repetition can shrink substantially;
already-compressed JPG/XLSX and random data often benefit little or not at all.
Compression is not a guarantee of fitting a receiving app's limits.

CompactText15.encode(byte[]) is pure Java, suitable for independent JVM use.
Consume selected payload bits most-significant-bit first, in big-endian groups of 15.
The final incomplete group is padded with ZERO bits on the RIGHT.
Symbol count = ceil(payload byte count * 8 / 15): packedSize for v4, size for v3.
Exact final alphabet (inclusive bounds):
  indexes     0 ..  6581 -> U+3400 .. U+4DB5  (6582 chars)
  indexes  6582 .. 27483 -> U+4E00 .. U+9FA5  (20902 chars)
  indexes 27484 .. 32767 -> U+AC00 .. U+C0A3  (5284 chars)
Total 32768 distinct, assigned BMP symbols, each one UTF-16 code unit.
Do NOT use the earlier 6592/27584 boundaries.

All alphabet symbols were verified stable under NFC and NFKC. Hangul decomposes
under NFD/NFKD: the receiver can restore NFC before decoding. This is not a claim
of stability under every normalization form. PC must check symbol count, padding,
full decoded size and SHA256 before saving. Compact15 itself is a reversible text
encoding; zlib is the separate lossless compression step. Neither is encryption.
SHA256 is not sender authentication. Android emits v4 when beneficial, otherwise v3.
PC compatibility with prior protocols is handled independently.

Original filenames are capped at 255 UTF-16 units without splitting a surrogate
pair. Missing/empty names use 'unnamed'. UI replaces controls/bidi/line separators.
JSON quotes, backslashes, controls and surrogates are escaped.

Clipboard / Gmail budgets
COPY always uses ClipData.newPlainText with the ENTIRE JSON and no sensitive extra.
The actual ClipData parcel is measured before setPrimaryClip. Cap: <=800*1024 bytes.
Above cap the UI reports actual byte/KiB size and refuses copying; no fallback,
provider, URI or fragmentation. After setPrimaryClip, getPrimaryClip().getItemAt(0)
.getText() must equal the full body before reporting confirmed copy. URI coercion
is never used. Unavailable/mismatched readback reports unconfirmed, not success
or a definite claim that nothing was copied.

Gmail ACTION_SEND text/plain uses EXTRA_TEXT only when the measured intent,
including simulated framework ClipData duplication and chooser nesting, is <=800 KiB.
Otherwise copy/readback must succeed before a prelaunch manual-paste dialog. Its
positive action opens a SUBJECT-ONLY composer: no body, URI or attachment. Gmail
launch failure offers a chooser; sending is always manual. No extra authentication.
These budgets are policy limits, not guaranteed OS capacity.

Storage / lifecycle
Original bytes, encoded body and current UI state remain in memory. There is no
provider or new content cache in v1.4. Removed v1.2 provider/store sources and tests.
Upgrades from v1.2 may retain old private cache files until Android evicts them or
app cache is cleared; v1.4 cannot expose them because that provider no longer exists.

A retained native Fragment owns the worker for reads, hashing, compression and encoding. Jobs
hold the application context only; stopped Activities detach listeners. Rotation
retains current conversion. No large content is saved in Bundles. Process death
requires selecting the file again. Interruption is requested on destruction, but
an external provider blocked inside read/query may delay its completion.

Build / validate
  cd /home/vhehdhkd/work/base64-transfer/android
  ./scripts/build.sh assembleDebug lintDebug
APK: app/build/outputs/apk/debug/app-debug.apk
Build log: build-validation.log
Lint: app/build/reports/lint-results-debug.txt

Existing personal-ledger/.tools/{jdk,sdk,gradle} are used read-only; Android build
cache, temporary files and the preserved debug key remain inside android.
local.properties points to the existing SDK. Build is offline. Gradle may require
sandbox escalation to open its local daemon socket. Nothing is committed/published.

Standalone JVM tests and deterministic vectors
  ./scripts/test-protocol.sh
  ./scripts/test-protocol.sh vectors 716800 > build/vector-716800.jsonl
  python3 tests/verify-vectors.py < build/vector-716800.jsonl
  ./scripts/test-protocol.sh vectors 716800 compressible | python3 tests/verify-vectors.py
  ./scripts/test-protocol.sh vectors 700000 random | python3 tests/verify-vectors.py

Generator stdout is one complete JSON envelope plus newline, encoded as UTF-8.
Default payload byte i = (i*31+7)&255. Optional 'random' uses deterministic xorshift32,
seed 0x15C0DE, operations x^=x<<13; x^=x>>>17; x^=x<<5; low byte per iteration.
Mode compressible produces all-zero bytes and a compressible-vector-SIZE.bin name.
Default filename vector-SIZE.bin; random mode random-vector-SIZE.bin. Repeated
default/zero vectors generally select v4; random/empty/small vectors may select v3.
SIZE=0 is empty; SIZE=1048576 rejects. Pure codec is CompactText15.java.

Tests cover all 32768 indexes, alphabet boundaries/highest index, uniqueness,
assigned BMP characters, NFC/NFKC stability, all final padding lengths, independent
bit-by-bit decode, random 700000/716800-byte roundtrips, known SHA256, strict read
limits, short/zero reads, cancellation and filename escaping. Cross-language JSON
vectors verify bytes/size/hash independently in Python. Physical keyboard history,
actual Android parcel measurements on a device, Gmail paste, clipboard readback,
TalkBack and lifecycle behavior still require device validation.

Compression validation additionally tests Inflater(false) lossless roundtrip,
original/packed sizes, complete zlib consumption, empty/small inputs and a range
of selection thresholds. Expected selection is checked against independently
constructed complete v3/v4 envelopes, not only compressed payload byte counts.
700000 and 716800-byte compressible and seeded random inputs are covered.

Gmail status: actual Gmail paste remains unverified. The user's reported 140 KB
success concerned OTHER applications; it is not a Gmail test result. Ordinary
clipboard readback success does not prove Gmail or keyboard-history compatibility.
