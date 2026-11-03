#!/usr/bin/env python3
"""Independent standard-library bit decoder for JVM compact15 JSON vectors."""
import hashlib
import json
import sys
import unicodedata

rows = [json.loads(line) for line in sys.stdin if line.strip()]
assert len(rows) == 1
row = rows[0]
assert set(row) == {'format', 'id', 'name', 'size', 'sha256', 'part', 'parts', 'data'}
assert row['format'] == 'text-transfer-v3'
assert 0 <= row['size'] < 1048576
assert row['part'] == row['parts'] == 1
assert len(row['data']) == (row['size'] * 8 + 14) // 15
assert unicodedata.normalize('NFKC', row['data']) == row['data']
result = bytearray()
pending = bits = 0
for char in row['data']:
    point = ord(char)
    if 0x3400 <= point <= 0x4DB5:
        index = point - 0x3400
    elif 0x4E00 <= point <= 0x9FA5:
        index = 6582 + point - 0x4E00
    elif 0xAC00 <= point <= 0xC0A3:
        index = 27484 + point - 0xAC00
    else:
        raise AssertionError('Invalid symbol')
    pending = (pending << 15) | index
    bits += 15
    while bits >= 8 and len(result) < row['size']:
        bits -= 8
        result.append((pending >> bits) & 255)
        pending &= (1 << bits) - 1
assert pending == 0, 'Nonzero padding'
assert len(result) == row['size']
assert hashlib.sha256(result).hexdigest() == row['id'] == row['sha256']
if row['name'].startswith('random-vector-'):
    expected = bytearray()
    state = 0x15C0DE
    for _ in range(row['size']):
        state ^= (state << 13) & 0xFFFFFFFF
        state ^= state >> 17
        state ^= (state << 5) & 0xFFFFFFFF
        expected.append(state & 255)
else:
    expected = bytes((i * 31 + 7) & 255 for i in range(row['size']))
assert result == expected
print(f"PASS: Java -> Python compact15: {len(result)} bytes, one envelope")
