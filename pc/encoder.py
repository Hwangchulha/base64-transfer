"""Bounded lossless file encoder, compatible with Android v3/v4 envelopes."""
import hashlib
import json
import zlib
from pathlib import Path
from decoder import DecodeError, MAX_FILE_BYTES


def compact_encode(raw):
    result = []
    accumulator = bits = 0
    for byte in raw:
        accumulator = (accumulator << 8) | byte
        bits += 8
        if bits >= 15:
            bits -= 15
            value = accumulator >> bits
            result.append(symbol(value))
            accumulator &= (1 << bits) - 1
    if bits:
        result.append(symbol(accumulator << (15-bits)))
    return ''.join(result)


def symbol(value):
    return chr(0x3400 + value) if value < 6582 else chr(0x4E00 + value - 6582) if value < 27484 else chr(0xAC00 + value - 27484)


def bounded_name(name):
    if not isinstance(name, str):
        raise DecodeError('파일 이름은 문자열이어야 합니다.')
    # Match Android's 255 UTF-16-unit bound without splitting an astral character.
    name = name or 'unnamed'
    try:
        return name.encode('utf-16-le')[:510].decode('utf-16-le', errors='ignore')
    except UnicodeError as exc:
        raise DecodeError('올바르지 않은 Unicode 파일 이름입니다.') from exc


def encode_bytes(raw, name):
    if not isinstance(raw, bytes):
        raise DecodeError('원본은 바이트 데이터여야 합니다.')
    if len(raw) >= MAX_FILE_BYTES:
        raise DecodeError('원본 파일은 1 MiB(1,048,576바이트) 미만이어야 합니다.')
    digest = hashlib.sha256(raw).hexdigest()
    envelope = dict(format='text-transfer-v3', id=digest, name=bounded_name(name),
                    size=len(raw), sha256=digest, part=1, parts=1, data=compact_encode(raw))
    original = json.dumps(envelope, ensure_ascii=False, separators=(',', ':'))
    packed = zlib.compress(raw)
    envelope.update(format='text-transfer-v4', encoding='zlib', packedSize=len(packed), data=compact_encode(packed))
    candidate = json.dumps(envelope, ensure_ascii=False, separators=(',', ':'))
    # JSON metadata is identical except format/compression fields. Compare actual
    # UTF-16 body sizes, including overhead; never expand the transmitted body.
    return candidate if len(candidate.encode('utf-16-le')) < len(original.encode('utf-16-le')) else original


def encode_file(path):
    path = Path(path)
    with path.open('rb') as source:
        raw = source.read(MAX_FILE_BYTES)
    return encode_bytes(raw, path.name)
