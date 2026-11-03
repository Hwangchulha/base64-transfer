Base64 Transfer — Android

Native Java app, Android 8.0 / API 26 or newer. No runtime library dependencies,
network permission, account login, password storage, or storage permission.
File access uses ACTION_OPEN_DOCUMENT (Storage Access Framework).

사용 방법
1. 파일 선택을 눌러 1 MiB(1,048,576바이트) 미만의 파일을 선택합니다.
2. 선택한 부분을 Gmail로 작성하거나 복사합니다.
3. Gmail에서 수신자를 입력하고 직접 보내기를 누릅니다. 앱은 전송 여부를
   확인하지 못하므로 자동으로 다음 부분으로 이동하지 않습니다.
4. 복사한 경우 메일·메신저 등 전달할 앱에 붙여넣어 PC로 보내세요.
   클립보드 복사는 PC와 자동 동기화되지 않습니다.
5. 이전/다음 버튼으로 부분을 선택하고 모든 부분을 PC에 전달합니다.

Protocol
Strict original byte limit: 0 <= size < 1,048,576. Actual stream reads enforce
this limit; provider size metadata is never trusted. At most 1,048,576 bytes
are consumed, including the byte proving rejection. Empty files produce one
part with empty data. CHUNK_BYTES = 100 * 1024 = 102400; at most 11 parts.
This replaces the earlier 200 KiB proposal because Android ACTION_SEND may
copy EXTRA_TEXT into ClipData, duplicating the body in the Binder parcel.

Each selected part is exactly one JSON string, with these fields in order:
{"format":"base64-transfer-v1","id":"<full lowercase SHA256>","name":"original.ext","size":123,"sha256":"<full lowercase SHA256>","part":1,"parts":1,"data":"<standard padded Base64>"}

SHA256 and id both hash the entire original file. Each raw chunk is encoded
independently. PC must decode each chunk BEFORE joining bytes in part order;
never concatenate padded Base64. Require matching metadata, reject conflicting
parts, and verify final size and SHA256 before saving. Base64 is not encryption;
SHA256 does not authenticate the sender.

Original display name is preserved in JSON up to 255 UTF-16 code units without
splitting a surrogate pair. Missing or empty names become 'unnamed'. UI replaces
control, formatting/bidi, line separator and unpaired surrogate characters.
JSON escapes quotes, backslashes, controls and surrogate code units.

Lifecycle and privacy
A retained native Fragment owns one worker and in-memory envelopes. File reads,
hashing and all Base64 conversion happen on its worker thread. Rotation retains
conversion and selected part; stopped Activities detach their listener. No large
payload enters saved-state Bundles. Process death discards the transfer: select
the file again. No persistent URI grant or local payload file is saved.
Finishing destroys the worker and requests interruption. Reads check interruption;
a provider blocked inside its own read/query may delay cancellation until that
call returns. Streams/cursors close when the operation exits. No stale callback
updates a destroyed Activity.

Sharing
ACTION_SEND uses text/plain, EXTRA_TEXT and package com.google.android.gm.
If Gmail launch fails, a chooser is offered. No body is put in a URI or explicit
ClipData on the actual send intent. A temporary measurement intent simulates
framework ClipData duplication and chooser nesting; payload parcels >=900 KiB
are rejected. A 100 KiB raw chunk is an application design cap, NOT a guaranteed
OS clipboard/Binder/Gmail maximum. Android's shared Binder buffer, concurrent
transactions and receiving apps can still reject it. Failures are explained.
Clipboard is marked sensitive (API 33 constant; compatible key on older APIs).
This suppresses previews on supporting systems; it does not encrypt the clipboard
or guarantee other apps cannot read it. Neither copy nor compose confirms delivery.

Build in this workspace
  cd /home/vhehdhkd/work/base64-transfer/android
  ./scripts/build.sh assembleDebug lintDebug
APK:
  app/build/outputs/apk/debug/app-debug.apk
Lint:
  app/build/reports/lint-results-debug.txt
  app/build/reports/lint-results-debug.html
Main packaging may copy the APK to the root distribution directory.

Tooling uses the existing personal-ledger/.tools/{jdk,sdk,gradle} read-only.
local.properties points to the existing SDK. The existing dependency cache was
copied into android/.gradle-home so cache locks and writes remain in this directory.
All build state, temporary files and the debug signing key are kept here. Builds
are offline; Gradle needs permission to open a local daemon socket in a sandbox.
TRANSFER_TOOLS_DIR can override the tooling path; update local.properties too.
The APK uses a debug key and is intended for testing/manual installation.

Standalone protocol tests (no Android SDK/framework or network required)
  ./scripts/test-protocol.sh
Covers empty file; 1, 2, 3 bytes; 102399, 102400, 102401 and 1048575 bytes;
exact-limit rejection; endless stream bounded consumption; short/zero reads;
misleading available(); SHA256 known answers; independent chunk reconstruction;
JSON escaping; safe filename handling; invalid parts; interruption.

Deterministic vector generation / interoperability
  ./scripts/test-protocol.sh vectors 102401 > build/vector-102401.jsonl
  python3 tests/verify-vectors.py < build/vector-102401.jsonl
Or:
  ./scripts/test-protocol.sh vectors 1048575 | python3 tests/verify-vectors.py

Generator stdout contains only JSONL (one complete envelope per line), directly
usable by a PC decoder. Byte i is (i * 31 + 7) & 255; name is vector-SIZE.bin.
Default vector size is 102401. SIZE=0 emits one empty chunk. SIZE=1048576 fails.
Python verification uses its independent json, base64 and hashlib libraries,
checks metadata, boundaries, decoded bytes, full size and SHA256.

Validation / limitations
The final build result is recorded in build-validation.log. Protocol tests and
Java-to-Python interoperability passed the sizes listed above. No physical-device
Gmail, chooser, clipboard, rotation or process-death test has been performed.
Lint initially reported 0 errors and 2 warnings: missing application icon and
Android 12 dataExtractionRules; this memory-only prototype saves no app data.
Native retained Fragments are deprecated but available at the supported API levels.
