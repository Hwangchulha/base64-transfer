import hashlib
import json
import random
import unicodedata
import unittest

from compact_text import decode_compact
from decoder import DecodeError, Transfer

ALPHABET = ''.join(chr(p) for a, b in ((0x3400, 0x4DB6), (0x4E00, 0x9FA6), (0xAC00, 0xC0A4))
                   for p in range(a, b))


def encode_reference(raw):
    # Independent bit-string reference used only for test vectors.
    binary = ''.join(f'{byte:08b}' for byte in raw)
    return ''.join(ALPHABET[int(binary[i:i+15].ljust(15, '0'), 2)] for i in range(0, len(binary), 15))


def envelope_v3(raw):
    digest = hashlib.sha256(raw).hexdigest()
    return dict(format='text-transfer-v3', id=digest, name='정확한 원본.bin', size=len(raw),
                sha256=digest, part=1, parts=1, data=encode_reference(raw))


class CompactTests(unittest.TestCase):
    def test_alphabet_stable_and_single_utf16_unit(self):
        self.assertEqual(len(ALPHABET), 32768)
        self.assertEqual(len(set(ALPHABET)), 32768)
        self.assertEqual(len(ALPHABET.encode('utf-16-le')), 65536)
        self.assertEqual(unicodedata.normalize('NFC', ALPHABET), ALPHABET)
        self.assertEqual(unicodedata.normalize('NFKC', ALPHABET), ALPHABET)
        self.assertTrue(all(not unicodedata.category(c).startswith(('C', 'M')) for c in ALPHABET))

    def test_all_padding_lengths_and_boundaries(self):
        rng = random.Random(1401)
        for size in list(range(46)) + [700000, 700*1024]:
            with self.subTest(size=size):
                raw = rng.randbytes(size)
                obj = envelope_v3(raw)
                text = json.dumps(obj, ensure_ascii=False)
                transfer = Transfer()
                transfer.add(text)
                self.assertEqual(transfer.assemble(), raw)
                if size == 700 * 1024:
                    self.assertLess(len(text.encode('utf-16-le')), 800 * 1024)

    def test_known_bytes_and_invalid_padding(self):
        self.assertEqual(decode_compact(ALPHABET[0], 1), b'\0')
        self.assertEqual(decode_compact(ALPHABET[32640], 1), b'\xff')
        with self.assertRaises(ValueError):
            decode_compact(ALPHABET[32641], 1)
        with self.assertRaises(ValueError):
            decode_compact('A', 1)
        with self.assertRaises(ValueError):
            decode_compact(ALPHABET[0] * 2, 1)

    def test_modified_text_rejected_by_hash(self):
        obj = envelope_v3(b'original')
        obj['data'] = ALPHABET[0] + obj['data'][1:]
        with self.assertRaisesRegex(DecodeError, 'SHA-256'):
            Transfer().add(json.dumps(obj, ensure_ascii=False))

    def test_decomposed_hangul_is_restored_before_decoding(self):
        raw = b'\xff' * 100
        obj = envelope_v3(raw)
        composed = obj['data']
        obj['data'] = unicodedata.normalize('NFD', composed)
        self.assertNotEqual(composed, obj['data'])
        transfer = Transfer()
        transfer.add(json.dumps(obj, ensure_ascii=False))
        self.assertEqual(transfer.assemble(), raw)


if __name__ == '__main__':
    unittest.main()
