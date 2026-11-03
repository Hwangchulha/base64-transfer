"""Tk regression tests; skip where Tk/display is unavailable."""
import base64
import hashlib
import json
import time
import unittest
from unittest.mock import patch
try:
    from app import App, tk
except ImportError:
    App = None


def envelope(raw):
    digest = hashlib.sha256(raw).hexdigest()
    return json.dumps(dict(format='base64-transfer-v2', id=digest, sha256=digest,
                          name='성능.bin', size=len(raw), part=1, parts=1,
                          data=base64.b64encode(raw).decode('ascii')))


@unittest.skipIf(App is None, 'Tk unavailable')
class GuiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.root.withdraw()
        self.app = App(self.root)
        self.errors = []
        self.error_patch = patch('app.messagebox.showerror', side_effect=lambda *a, **k: self.errors.append(a))
        self.error_patch.start()

    def tearDown(self):
        self.error_patch.stop()
        if not self.app.closed:
            self.app.close()

    def drain(self):
        deadline = time.monotonic() + 10
        while self.app.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.005)
        self.assertFalse(self.app.busy)

    def test_full_input_bounded_preview_and_async_decode(self):
        raw = bytes(range(256)) * 4095
        body = envelope(raw)
        with patch('app.read_text', return_value=body):
            self.app.paste()
        self.assertEqual(self.app.input_text, body)
        self.assertLess(len(self.app.text.get('1.0', 'end-1c')), 5000)
        self.assertEqual(str(self.app.text['state']), 'disabled')
        self.app.add()
        self.assertTrue(self.app.busy)
        self.app.set_input('must not replace pending input')
        self.assertEqual(self.app.input_text, body)
        self.drain()
        self.assertEqual(self.app.transfer.assemble(), raw)
        self.assertEqual(self.app.input_text, '')
        self.assertEqual(str(self.app.save_button['state']), 'normal')
        self.assertEqual(self.errors, [])

    def test_new_file_replaces_completed_transfer_only_after_validation(self):
        from encoder import encode_bytes
        self.app.set_input(encode_bytes(b'old', 'old.bin'))
        self.app.add(); self.drain()
        self.app.set_input(encode_bytes(b'new' * 10000, 'new.bin'))
        self.app.add(); self.drain()
        self.assertEqual(self.app.transfer.assemble(), b'new' * 10000)
        self.assertEqual(self.app.transfer.filename, 'new.bin')
        self.assertEqual(self.errors, [])

    def test_bad_new_input_cannot_save_previous_file(self):
        self.app.set_input(envelope(b'previous'))
        self.app.add(); self.drain()
        self.app.set_input('broken JSON')
        self.assertEqual(str(self.app.save_button['state']), 'disabled')
        with patch('app.filedialog.asksaveasfilename') as dialog:
            self.app.save()
            dialog.assert_not_called()
        self.app.add(); self.drain()
        self.assertEqual(self.app.input_text, 'broken JSON')
        self.assertEqual(self.app.transfer.assemble(), b'previous')
        self.assertEqual(str(self.app.save_button['state']), 'disabled')
        self.assertTrue(self.errors)

    def test_close_while_decoding(self):
        import threading
        started = threading.Event()
        original = self.app.decode_input
        def delayed(candidate, value):
            started.set()
            time.sleep(.05)
            return original(candidate, value)
        with patch.object(self.app, 'decode_input', side_effect=delayed):
            self.app.set_input(envelope(b'closing'))
            self.app.add()
            self.assertTrue(started.wait(1))
            self.app.close()
            self.app.future.result(timeout=2)
        self.assertTrue(self.app.closed)

    def test_submission_failure_keeps_input_and_recovers_controls(self):
        value = envelope(b'retry')
        self.app.set_input(value)
        with patch.object(self.app.executor, 'submit', side_effect=RuntimeError('Unavailable')):
            self.app.add()
        self.assertFalse(self.app.busy)
        self.assertEqual(self.app.input_text, value)
        self.assertEqual(str(self.app.add_button['state']), 'normal')
        self.assertTrue(self.errors)


if __name__ == '__main__':
    unittest.main()
