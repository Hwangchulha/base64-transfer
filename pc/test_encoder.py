import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch
from decoder import Transfer, DecodeError, MAX_FILE_BYTES
from encoder import encode_bytes, encode_file, compact_encode, bounded_name
from compact_text import decode_compact
from test_compact import encode_reference


class EncoderTests(unittest.TestCase):
    def test_bit_boundaries_and_reference(self):
        rng = random.Random(7)
        for size in range(0, 80):
            raw = bytes(rng.randrange(256) for _ in range(size))
            text = compact_encode(raw)
            self.assertEqual(text, encode_reference(raw))
            self.assertEqual(decode_compact(text, size), raw)

    def test_roundtrip_compressed_random_and_maximum(self):
        rng = random.Random(11)
        random_data = bytes(rng.randrange(256) for _ in range(700*1024))
        for raw, expected in [(b'', 'text-transfer-v3'), (b'x', 'text-transfer-v3'),
                              (b'a'*700*1024, 'text-transfer-v4'),
                              (random_data, 'text-transfer-v3'),
                              (b'\xff'*(MAX_FILE_BYTES-1), 'text-transfer-v4')]:
            with self.subTest(size=len(raw), expected=expected):
                body = encode_bytes(raw, '보고서_😀.xlsx')
                self.assertEqual(json.loads(body)['format'], expected)
                transfer = Transfer(); transfer.add(body)
                self.assertEqual(transfer.assemble(), raw)
                self.assertEqual(transfer.filename, '보고서_😀.xlsx')

    def test_overhead_falls_back_and_bad_inputs(self):
        # Compressible bytes alone are shorter, but the extra v4 fields cost more.
        self.assertEqual(json.loads(encode_bytes(b'a'*30, 'a'))['format'], 'text-transfer-v3')
        for raw in [b'x'*MAX_FILE_BYTES, 'text', bytearray(b'abc')]:
            with self.assertRaises(DecodeError):
                encode_bytes(raw, 'a')
        with self.assertRaises(DecodeError):
            encode_bytes(b'x', '\ud800')

    def test_name_utf16_bound_and_special_characters(self):
        self.assertEqual(bounded_name('a'*254+'😀'), 'a'*254)
        self.assertEqual(bounded_name('😀'*128), '😀'*127)
        for name in ['', '보고서"\\\n😀.txt', '😀'*128]:
            body = encode_bytes(b'abc', name)
            self.assertLessEqual(len(json.loads(body)['name'].encode('utf-16-le')), 510)
            transfer = Transfer(); transfer.add(body)
            self.assertEqual(transfer.assemble(), b'abc')

    def test_file_read_bound_and_no_source_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / '원본.bin'
            source.write_bytes(b'unchanged')
            body = encode_file(source)
            transfer = Transfer(); transfer.add(body)
            self.assertEqual(transfer.assemble(), b'unchanged')
            self.assertEqual(source.read_bytes(), b'unchanged')
        opened = mock_open(read_data=b'x'*MAX_FILE_BYTES)
        with patch.object(Path, 'open', opened), self.assertRaises(DecodeError):
            encode_file('large.bin')
        opened().read.assert_called_once_with(MAX_FILE_BYTES)
