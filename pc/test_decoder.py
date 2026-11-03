import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from check_vectors import load_vectors
from decoder import (CHUNK_BYTES, MAX_ENVELOPES, MAX_FILE_BYTES, MAX_NAME_CHARS,
                     MAX_PARTS, MAX_TEXT_CHARS, DecodeError, Transfer,
                     parse_envelopes, safe_filename)


def envelopes(raw, name='원본 🐈.bin'):
    digest = hashlib.sha256(raw).hexdigest()
    parts = max(1, (len(raw) + CHUNK_BYTES - 1) // CHUNK_BYTES)
    return [dict(format='base64-transfer-v1', id=digest, name=name, size=len(raw),
                 sha256=digest, part=i + 1, parts=parts,
                 data=base64.b64encode(raw[i * CHUNK_BYTES:(i + 1) * CHUNK_BYTES]).decode('ascii'))
            for i in range(parts)]


def text(items):
    return ' \n\t'.join(json.dumps(item, ensure_ascii=False) for item in items)


class DecoderTests(unittest.TestCase):
    def test_boundaries_reversed_duplicates_unicode_empty(self):
        self.assertEqual(CHUNK_BYTES, 102400)
        self.assertEqual(MAX_PARTS, 11)
        for size in (0, 1, 2, 3, CHUNK_BYTES - 1, CHUNK_BYTES, CHUNK_BYTES + 1, MAX_FILE_BYTES - 1):
            with self.subTest(size=size):
                raw = (bytes(range(256)) * ((size + 255) // 256))[:size]
                parts = envelopes(raw)
                transfer = Transfer()
                self.assertEqual(transfer.add(text(list(reversed(parts)) + [parts[0]])), len(parts))
                self.assertEqual(transfer.add(text([parts[0]])), 0)
                self.assertEqual(transfer.assemble(), raw)
                self.assertEqual(transfer.filename, '원본 🐈.bin')
                self.assertEqual(transfer.missing, ())

    def test_missing_clear(self):
        parts = envelopes(b'x' * (CHUNK_BYTES + 1))
        transfer = Transfer()
        transfer.add(text([parts[1]]))
        self.assertEqual(transfer.missing, (1,))
        self.assertIn('1', transfer.status)
        with self.assertRaises(DecodeError):
            transfer.assemble()
        transfer.clear()
        self.assertEqual(transfer.missing, ())
        with self.assertRaises(DecodeError):
            transfer.assemble()

    def test_corruption_rejected_atomically(self):
        parts = envelopes(b'x' * (CHUNK_BYTES + 1))
        transfer = Transfer()
        transfer.add(text([parts[0]]))
        corrupt = dict(parts[1], data='eQ==')
        with self.assertRaisesRegex(DecodeError, 'SHA-256'):
            transfer.add(text([corrupt]))
        self.assertEqual(transfer.missing, (2,))
        transfer.add(text([parts[1]]))
        self.assertEqual(len(transfer.assemble()), CHUNK_BYTES + 1)

    def test_conflicting_duplicate_and_metadata(self):
        parts = envelopes(b'x' * (CHUNK_BYTES + 1))
        transfer = Transfer()
        transfer.add(text([parts[0]]))
        bad_duplicate = dict(parts[0], data=base64.b64encode(b'y' * CHUNK_BYTES).decode())
        for candidate in (bad_duplicate, dict(parts[1], name='different.bin'), envelopes(b'other')[0]):
            with self.subTest(candidate=candidate['name']):
                with self.assertRaises(DecodeError):
                    transfer.add(text([candidate]))
                self.assertEqual(transfer.missing, (2,))
        fresh = Transfer()
        with self.assertRaises(DecodeError):
            fresh.add(text([parts[0], dict(parts[1], name='conflict')]))
        with self.assertRaises(DecodeError):
            fresh.assemble()
        self.assertEqual(fresh.add(text(parts)), 2)

    def test_invalid_fields_types_and_bounds(self):
        original = envelopes(b'x')[0]
        mutations = [('size', -1), ('size', MAX_FILE_BYTES), ('size', True), ('size', 1.0),
                     ('part', True), ('parts', False), ('part', 0), ('part', 2), ('parts', 12),
                     ('parts', 2), ('id', 'a' * 64), ('sha256', 'A' * 64), ('id', '0' * 63),
                     ('name', ''), ('name', 'x' * (MAX_NAME_CHARS + 1)), ('name', '\ud800'),
                     ('data', 1), ('name', []), ('format', None), ('format', 'other'),
                     ('data', '!!!!'), ('data', 'eA= '), ('data', 'eB=='), ('data', 'eA==='),
                     ('data', 'é===')]
        for key, value in mutations:
            with self.subTest(key=key, value=repr(value)[:30]):
                with self.assertRaises(DecodeError):
                    parse_envelopes(json.dumps(dict(original, **{key: value})))
        for obj in ({}, dict(original, extra=1), [], dict(original, size='1')):
            with self.assertRaises(DecodeError):
                parse_envelopes(json.dumps(obj))

    def test_invalid_chunk_lengths(self):
        parts = envelopes(b'x' * (CHUNK_BYTES + 1))
        for index, raw in ((0, b'x' * (CHUNK_BYTES - 1)), (1, b'xx')):
            bad = dict(parts[index], data=base64.b64encode(raw).decode())
            with self.assertRaises(DecodeError):
                parse_envelopes(text([bad]))

    def test_json_and_input_bounds(self):
        one = text(envelopes(b''))
        for value in ('', ' ', 'email\n' + one, one + 'signature', one[:-1],
                      '[]', '{"x":1,"x":2}', '{"x":NaN}', '[' * 2000,
                      ' ' * (MAX_TEXT_CHARS + 1), one * (MAX_ENVELOPES + 1)):
            with self.subTest(prefix=value[:20]):
                with self.assertRaises(DecodeError):
                    parse_envelopes(value)
        self.assertEqual(len(parse_envelopes(one + one)), 2)
        # A later parse error must not add the earlier valid part.
        transfer = Transfer()
        with self.assertRaises(DecodeError):
            transfer.add(one + 'bad')
        self.assertEqual(transfer.add(one), 1)

    def test_safe_names(self):
        for source, expected in [('C:\\temp\\한글.txt', '한글.txt'), ('../../a.png', 'a.png'),
                                 ('../..', 'received-file'), ('a/', 'received-file'),
                                 ('CON.txt', '_CON.txt'), ('aux', '_aux'), ('COM¹.png', '_COM¹.png'),
                                 ('LPT9', '_LPT9'), ('CONIN$', '_CONIN$'), ('x:?.txt ', 'x__.txt'),
                                 ('hello 🐈.tar.gz', 'hello 🐈.tar.gz')]:
            self.assertEqual(safe_filename(source), expected)
        for name in ('한' * 251 + '.txt', '🐈' * 500 + '.png', 'a.' + '한' * 500):
            safe = safe_filename(name)
            self.assertLessEqual(len(safe.encode('utf-8')), 240)
            self.assertLessEqual(len(safe.encode('utf-16-le')) // 2, 240)
        self.assertFalse(safe_filename('CONlong.' + 'a' * 236).startswith('CON.'))
        original = '한' * 251 + '.txt'
        transfer = Transfer()
        transfer.add(text(envelopes(b'', original)))
        self.assertTrue(transfer.filename.endswith('.txt'))
        with self.assertRaises(DecodeError):
            transfer.add(text(envelopes(b'', transfer.filename)))

    def test_vector_loader(self):
        # Keep all test writes inside the assigned PC directory.
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            folder = Path(directory)
            raw = b'Android interop\x00\xff'
            vector, original = folder / 'envelopes.txt', folder / 'original.bin'
            vector.write_text(text(envelopes(raw)), encoding='utf-8')
            original.write_bytes(raw)
            self.assertEqual(load_vectors([vector], original).assemble(), raw)
            original.write_bytes(b'wrong')
            with self.assertRaises(DecodeError):
                load_vectors([vector], original)


if __name__ == '__main__':
    unittest.main()
