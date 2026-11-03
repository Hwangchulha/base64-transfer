"""Real Windows clipboard tests in a PRIVATE window station, never user clipboard."""
import os
import subprocess
import sys
import unittest
from pathlib import Path


from windows_test_station import station


def isolated_check():
    name = 'Base64ClipboardTest' + str(os.getpid())
    station(name, True)  # Fail closed before ANY clipboard action if isolation fails.
    import hashlib
    import random
    import time
    from app import App, tk
    from encoder import encode_bytes
    from clipboard_io import read_text, write_text
    from unittest.mock import patch
    root = tk.Tk(); root.withdraw()
    app = App(root); app.open_encoder()
    view = app.encoder_window; view.window.withdraw()
    errors = []
    rng = random.Random(42)
    cases = [b'', b'a' * 716800, rng.randbytes(120000) + b'x' * 20000, rng.randbytes(716800)]
    with patch('encode_window.messagebox.showerror', side_effect=lambda *a, **k: errors.append(a)), patch('app.messagebox.showerror', side_effect=lambda *a, **k: errors.append(a)):
        for raw in cases:
            body = encode_bytes(raw, 'Unicode_😀.bin')
            # Legacy Tk write -> native read, including same-process owner.
            root.clipboard_clear(); root.clipboard_append(body); root.update_idletasks()
            assert read_text(root) == body, 'Native read of legacy Tk owner differs'
            view.payload = body
            view.copy_payload()  # Real native write + exact readback.
            assert not errors, errors
            assert read_text(root) == body
            app.paste(); assert app.input_text == body
            app.add()
            deadline = time.monotonic() + 15
            while app.busy and time.monotonic() < deadline:
                root.update(); time.sleep(.005)
            assert not app.busy and not errors, errors
            assert app.transfer.assemble() == raw
        # Separate-process read of native clipboard, independent of Tk's cache.
        expected = hashlib.sha256(body.encode('utf-8')).hexdigest()
        output = subprocess.check_output([sys.executable, __file__, '--read-station', name], text=True, timeout=20)
        assert output.strip() == expected
        alphabet = ''.join(chr(i) for a,b in [(0x3400,0x4DB5),(0x4E00,0x9FA5),(0xAC00,0xC0A3)] for i in range(a,b+1))
        write_text(root, alphabet)
        assert read_text(root) == alphabet
        app.close()
        second = tk.Tk(); second.withdraw()
        assert read_text(second) == alphabet, 'Native clipboard lost after writer window closes'
        subprocess.run([sys.executable, __file__, '--write-station', name], check=True, timeout=20)
        assert read_text(second) == '㐀a😀' * 10000, 'Clipboard lost after writer process exits'
        second.destroy()
    print('PASS: real isolated clipboard, same-process GUI, cross-process, full alphabet, writer close')


@unittest.skipUnless(sys.platform == 'win32', 'Windows clipboard requires Windows')
class WindowsClipboardTests(unittest.TestCase):
    def test_real_clipboard_in_isolated_window_station(self):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--isolated'],
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS: real isolated clipboard', result.stdout)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--isolated':
        isolated_check()
    elif len(sys.argv) > 2 and sys.argv[1] == '--write-station':
        station(sys.argv[2], False)
        import tkinter as tk
        from clipboard_io import write_text
        root = tk.Tk(); root.withdraw()
        write_text(root, '㐀a😀' * 10000)
        root.destroy()
    elif len(sys.argv) > 2 and sys.argv[1] == '--read-station':
        station(sys.argv[2], False)
        import hashlib
        import tkinter as tk
        from clipboard_io import read_text
        root = tk.Tk(); root.withdraw()
        print(hashlib.sha256(read_text(root).encode('utf-8')).hexdigest())
        root.destroy()
    else:
        unittest.main()
