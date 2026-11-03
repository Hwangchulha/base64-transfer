"""Package the installable debug APK and offline PC receiver without caches/keys."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import shutil

root = Path(__file__).resolve().parent
apk = root / 'android/app/build/outputs/apk/debug/app-debug.apk'
required = ['START-HERE.txt', 'PROTOCOL.txt', 'pc/app.py', 'pc/decoder.py',
            'pc/encoder.py', 'pc/encode_window.py', 'pc/test_encoder.py', 'pc/test_encode_gui.py',
            'pc/compact_text.py', 'pc/test_compact.py', 'pc/test_compression.py',
            'pc/launch.cmd', 'pc/README.txt', 'pc/test_decoder.py',
            'pc/check_vectors.py', 'pc/build_windows.py', 'pc/test_gui.py', 'android/README.txt']
for name in required:
    if not (root / name).is_file():
        raise SystemExit('Missing: ' + name)
if not apk.is_file():
    raise SystemExit('Build Android debug APK first.')
dist = root / 'dist'
dist.mkdir(exist_ok=True)
shutil.copyfile(apk, dist / 'base64-transfer-debug.apk')
with ZipFile(dist / 'base64-transfer.zip', 'w', ZIP_DEFLATED) as archive:
    for name in required:
        archive.write(root / name, name)
    archive.write(apk, 'base64-transfer-debug.apk')
    if (dist / 'Base64Restore.exe').is_file():
        archive.write(dist / 'Base64Restore.exe', 'Base64Restore.exe')
print(dist / 'base64-transfer.zip')
