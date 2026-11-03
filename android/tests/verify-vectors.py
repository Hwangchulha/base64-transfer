#!/usr/bin/env python3
"""Independent standard-library decoder for deterministic JVM JSONL vectors."""
import base64
import hashlib
import json
import sys

rows = [json.loads(line) for line in sys.stdin if line.strip()]
assert rows, 'No vectors received'
first = rows[0]
assert set(first) == {'format', 'id', 'name', 'size', 'sha256', 'part', 'parts', 'data'}
assert first['format'] == 'base64-transfer-v2'
assert 0 <= first['size'] < 1048576
assert first['parts'] == 1
assert len(rows) == first['parts']
chunks = {}
for row in rows:
    for key in ('format', 'id', 'name', 'size', 'sha256', 'parts'):
        assert row[key] == first[key], key
    assert 1 <= row['part'] <= first['parts'] and row['part'] not in chunks
    chunk = base64.b64decode(row['data'], validate=True)
    assert len(chunk) == first['size']
    chunks[row['part']] = chunk
joined = b''.join(chunks[i] for i in range(1, first['parts'] + 1))
assert len(joined) == first['size']
assert hashlib.sha256(joined).hexdigest() == first['id'] == first['sha256']
assert joined == bytes((i * 31 + 7) & 255 for i in range(first['size']))
print(f"PASS: Java -> Python: {len(joined)} bytes, {len(rows)} parts")
