import hashlib
import gzip
import json
import unittest
import zlib
from decoder import DecodeError, Transfer
from test_compact import encode_reference


def compressed_envelope(raw, packed=None):
    if packed is None:
        packed = zlib.compress(raw, 9)
    digest = hashlib.sha256(raw).hexdigest()
    return dict(format='text-transfer-v4', id=digest, name='압축 원본.xlsx', size=len(raw),
                sha256=digest, part=1, parts=1, encoding='zlib', packedSize=len(packed),
                data=encode_reference(packed))


def text(obj):
    return json.dumps(obj, ensure_ascii=False)


class CompressionTests(unittest.TestCase):
    def test_large_roundtrip_and_original_hash(self):
        raw = (b'lossless report\x00\xff' * 65536)[:1048575]
        obj = compressed_envelope(raw)
        tr = Transfer(); tr.add(text(obj))
        self.assertEqual(tr.assemble(), raw)
        self.assertTrue(tr.compressed)
        self.assertEqual(tr.packed_size, obj['packedSize'])
        self.assertEqual(tr.add(text(obj)), 0)
        self.assertLess(len(text(obj)), 6000)
        damaged = dict(obj, id='0'*64, sha256='0'*64)
        with self.assertRaisesRegex(DecodeError, 'SHA-256'):
            Transfer().add(text(damaged))

    def test_truncated_trailing_concatenated_and_checksum(self):
        raw = b'a' * 700000
        good = zlib.compress(raw)
        for packed in (good[:-1], good + b'junk', good + good, good[:-1] + bytes([good[-1] ^ 1])):
            with self.subTest(length=len(packed)):
                with self.assertRaises(DecodeError):
                    Transfer().add(text(compressed_envelope(raw, packed)))

    def test_inflation_bound_and_declared_size(self):
        raw = b'a' * 700000
        obj = compressed_envelope(raw)
        obj['size'] = 2000  # Packed bytes fit; claimed inflated size is deliberately false.
        with self.assertRaises(DecodeError):
            Transfer().add(text(obj))
        obj = compressed_envelope(raw)
        obj['size'] += 1
        with self.assertRaises(DecodeError):
            Transfer().add(text(obj))

    def test_wrong_wrapper_dictionary_and_invalid_fields(self):
        raw = b'a' * 10000
        raw_deflater = zlib.compressobj(wbits=-15)
        raw_deflate = raw_deflater.compress(raw) + raw_deflater.flush()
        dict_deflater = zlib.compressobj(zdict=b'aaaaaa')
        with_dict = dict_deflater.compress(raw) + dict_deflater.flush()
        for packed in (raw_deflate, gzip.compress(raw), with_dict):
            with self.assertRaises(DecodeError):
                Transfer().add(text(compressed_envelope(raw, packed)))
        obj = compressed_envelope(raw)
        for key, value in [('packedSize', True), ('packedSize', 0), ('packedSize', len(raw)),
                           ('packedSize', obj['packedSize'] + 1), ('encoding', 'gzip'), ('parts', 2)]:
            with self.assertRaises(DecodeError):
                Transfer().add(text(dict(obj, **{key: value})))
        with self.assertRaises(DecodeError):
            Transfer().add(text(dict(obj, extra=1)))

    def test_damage_messages_identify_length_character_and_inflate_stages(self):
        obj = compressed_envelope(b'a' * 10000)
        with self.assertRaisesRegex(DecodeError, '문자 수'):
            Transfer().add(text(dict(obj, data=obj['data'][:-1])))
        with self.assertRaisesRegex(DecodeError, '문자 또는 끝부분'):
            Transfer().add(text(dict(obj, data='?' + obj['data'][1:])))
        with self.assertRaisesRegex(DecodeError, '압축 해제에 실패'):
            Transfer().add(text(dict(obj, data='㐀' + obj['data'][1:])))

    def test_failed_batch_leaves_previous_transfer_unchanged(self):
        good = compressed_envelope(b'a' * 10000)
        tr = Transfer(); tr.add(text(good))
        broken = compressed_envelope(b'b' * 10000)
        broken['packedSize'] = 0
        with self.assertRaises(DecodeError):
            tr.add(text(broken))
        self.assertEqual(tr.assemble(), b'a' * 10000)


if __name__ == '__main__':
    unittest.main()
