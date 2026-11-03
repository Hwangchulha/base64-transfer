"""Build and smoke-test on Windows, then place EXE on the real Desktop."""
import ctypes
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

if sys.platform != 'win32':
    raise SystemExit('Run this builder on Windows.')
root = Path(__file__).resolve().parent
subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(root), '-v'], check=True)
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                '--onefile', '--windowed', '--name', 'Base64Restore',
                '--distpath', str(root / 'dist'), '--workpath', str(root / 'build'),
                '--specpath', str(root), str(root / 'app.py')], cwd=root, check=True)
exe = root / 'dist/Base64Restore.exe'
report = root / 'build/frozen-self-test.txt'
report.unlink(missing_ok=True)
subprocess.run([str(exe), '--self-test-report', str(report)], check=True, timeout=60)
if report.read_text(encoding='utf-8') != 'PASS: bundled Tk UI and decoder\n':
    raise SystemExit('Frozen self-test did not pass.')
buffer = ctypes.create_unicode_buffer(32768)
if ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buffer) != 0:
    raise SystemExit('Cannot resolve Desktop.')
desktop = Path(buffer.value)
destination = desktop / 'Base64Restore.exe'
if destination.exists():
    if hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(exe.read_bytes()).digest():
        backup_dir = root / 'backups'
        backup_dir.mkdir(exist_ok=True)
        backup = backup_dir / ('Base64Restore-' + hashlib.sha256(destination.read_bytes()).hexdigest()[:10] + '.previous.exe')
        if not backup.exists():
            shutil.copy2(destination, backup)
        if '--build-only' not in sys.argv:
            shutil.copy2(exe, destination)
else:
    if '--build-only' not in sys.argv:
        with destination.open('xb') as output, exe.open('rb') as source:
            shutil.copyfileobj(source, output)
print(('BUILT_EXE=' + str(exe)) if '--build-only' in sys.argv else ('DESKTOP_EXE=' + str(destination)))
print('SHA256=' + hashlib.sha256(exe.read_bytes()).hexdigest())
print(report.read_text(encoding='utf-8').strip())
