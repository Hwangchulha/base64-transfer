"""Encode UI: async roundtrip, bounded preview, explicit full copy/save, failure/close."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from decoder import Transfer
try:
    from app import App, tk
except ImportError:
    App = None


@unittest.skipIf(App is None, 'Tk unavailable')
class EncodeGuiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.root.withdraw()
        self.app = App(self.root)
        self.app.open_encoder()
        self.view = self.app.encoder_window
        self.view.window.withdraw()
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name) / '보고서.bin'
        self.source.write_bytes(bytes(range(256)) * 2800)
        self.errors = []
        self.patcher = patch('encode_window.messagebox.showerror', side_effect=lambda *a, **k: self.errors.append(a))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if not self.app.closed:
            self.app.close()
        self.temp.cleanup()

    def drain(self):
        deadline = time.monotonic() + 15
        while self.view.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.005)
        self.assertFalse(self.view.busy)

    def test_roundtrip_copy_save_and_bounded_preview(self):
        self.view.start(self.source)
        self.assertTrue(self.view.busy)
        self.assertEqual(str(self.view.copy_button['state']), 'disabled')
        self.drain()
        transfer = Transfer(); transfer.add(self.view.payload)
        self.assertEqual(transfer.assemble(), self.source.read_bytes())
        self.assertLess(len(self.view.preview.get('1.0', 'end-1c')), 400)
        with patch.object(self.view.window, 'clipboard_clear') as clear, patch.object(self.view.window, 'clipboard_append') as append:
            self.view.copy_payload()
            clear.assert_called_once()
            append.assert_called_once_with(self.view.payload)
        destination = Path(self.temp.name) / 'encoded.txt'
        with patch('encode_window.filedialog.asksaveasfilename', return_value=str(destination)):
            self.view.save_payload()
            self.assertEqual(destination.read_text(encoding='utf-8'), self.view.payload)
            self.view.save_payload()  # Existing files must never be overwritten.
        self.assertEqual(len(self.errors), 1)

    def test_failed_selection_clears_stale_output_and_recovers(self):
        self.view.start(self.source); self.drain()
        self.view.start(Path(self.temp.name) / 'missing.bin'); self.drain()
        self.assertEqual(self.view.payload, '')
        self.assertEqual(str(self.view.copy_button['state']), 'disabled')
        self.assertEqual(str(self.view.pick['state']), 'normal')
        self.assertTrue(self.errors)
        with patch.object(self.view.executor, 'submit', side_effect=RuntimeError('Unavailable')):
            self.view.start(self.source)
        self.assertFalse(self.view.busy)
        self.assertEqual(str(self.view.pick['state']), 'normal')

    def test_close_while_encoding_and_reopen(self):
        import threading
        from encoder import encode_file
        started = threading.Event()
        def delayed(path):
            started.set(); time.sleep(.05)
            return encode_file(path)
        with patch('encode_window.encode_file', side_effect=delayed):
            self.view.start(self.source)
            self.assertTrue(started.wait(1))
            future = self.view.future
            self.view.close()
            future.result(timeout=3)
        self.app.open_encoder()
        self.assertIsNot(self.app.encoder_window, self.view)
        self.assertFalse(self.app.encoder_window.closed)
