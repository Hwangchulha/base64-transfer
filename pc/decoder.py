"""Bounded, offline Base64 Transfer v1 decoder; no GUI or filesystem access."""
import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass

FORMAT = 'base64-transfer-v1'
CHUNK_BYTES = 100 * 1024
MAX_FILE_BYTES = 1024 * 1024  # Exclusive.
MAX_PARTS = (MAX_FILE_BYTES - 1 + CHUNK_BYTES - 1) // CHUNK_BYTES
MAX_TEXT_CHARS = 2 * 1024 * 1024
MAX_ENVELOPES = 32
MAX_NAME_CHARS = 1024
FIELDS = {'format', 'id', 'name', 'size', 'sha256', 'part', 'parts', 'data'}
HEX = re.compile(r'[0-9a-f]{64}\Z')


class DecodeError(ValueError):
    """Invalid input or incomplete/invalid transfer."""


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DecodeError('Duplicate JSON field: ' + key)
        result[key] = value
    return result


def _bad_constant(value):
    raise DecodeError('Invalid JSON constant: ' + value)


@dataclass(frozen=True)
class Chunk:
    metadata: tuple
    part: int
    raw: bytes


def _validate(obj):
    if type(obj) is not dict or set(obj) != FIELDS:
        raise DecodeError('Each envelope must have exactly the eight protocol fields.')
    for key in ('format', 'id', 'name', 'sha256', 'data'):
        if type(obj[key]) is not str:
            raise DecodeError(key + ' must be a string.')
    for key in ('size', 'part', 'parts'):
        if type(obj[key]) is not int:  # bool is deliberately not accepted.
            raise DecodeError(key + ' must be an integer.')
    if obj['format'] not in (FORMAT, 'base64-transfer-v2'):
        raise DecodeError('Unsupported format.')
    if not HEX.fullmatch(obj['id']) or not HEX.fullmatch(obj['sha256']):
        raise DecodeError('id and sha256 must be full lowercase SHA-256 hex.')
    if obj['id'] != obj['sha256']:
        raise DecodeError('id must equal sha256.')
    name = obj['name']
    if not 1 <= len(name) <= MAX_NAME_CHARS or any(0xD800 <= ord(c) <= 0xDFFF for c in name):
        raise DecodeError('Invalid filename length or Unicode.')
    size = obj['size']
    if not 0 <= size < MAX_FILE_BYTES:
        raise DecodeError('File size must be 0 through 1,048,575 bytes.')
    single = obj['format'] == 'base64-transfer-v2'
    parts = 1 if single else max(1, (size + CHUNK_BYTES - 1) // CHUNK_BYTES)
    if obj['parts'] != parts or not 1 <= obj['part'] <= parts:
        raise DecodeError('Invalid part count or part number for file size.')
    expected = size if single else CHUNK_BYTES if obj['part'] < parts else size - CHUNK_BYTES * (parts - 1)
    data = obj['data']
    if len(data) != 4 * ((expected + 2) // 3):
        raise DecodeError('Base64 length does not match this chunk.')
    try:
        raw = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise DecodeError('Malformed Base64.') from exc
    if len(raw) != expected or base64.b64encode(raw).decode('ascii') != data:
        raise DecodeError('Invalid chunk length or noncanonical padded Base64.')
    metadata = tuple(obj[k] for k in ('format', 'id', 'name', 'size', 'sha256', 'parts'))
    return Chunk(metadata, obj['part'], raw)


def parse_envelopes(text):
    """Read consecutive whole JSON objects, optionally separated by whitespace."""
    if type(text) is not str or len(text) > MAX_TEXT_CHARS:
        raise DecodeError('Paste limit is 2,097,152 characters per Add.')
    parser = json.JSONDecoder(object_pairs_hook=_object, parse_constant=_bad_constant)
    result = []
    position = 0
    try:
        while position < len(text):
            while position < len(text) and text[position] in ' \r\n\t':
                position += 1
            if position == len(text):
                break
            if len(result) >= MAX_ENVELOPES:
                raise DecodeError('At most 32 envelopes per Add.')
            obj, position = parser.raw_decode(text, position)
            result.append(_validate(obj))
    except (ValueError, RecursionError) as exc:
        if isinstance(exc, DecodeError):
            raise
        raise DecodeError('Invalid JSON. Paste only complete envelope blocks.') from exc
    if not result:
        raise DecodeError('Paste at least one complete JSON envelope.')
    return result


def safe_filename(name):
    """Portable basename; retain Unicode/extensions while neutralizing device names."""
    name = re.split(r'[/\\]', name)[-1]
    name = ''.join('_' if ord(c) < 32 or ord(c) == 127 or c in '<>:"|?*' else c for c in name)
    name = name.rstrip(' .')
    if not name or name in ('.', '..'):
        return 'received-file'
    stem = name.split('.', 1)[0].rstrip(' ').upper()
    if stem in {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'} or re.fullmatch(r'(COM|LPT)[1-9¹²³]', stem):
        name = '_' + name
    # UTF-8 <=240 bytes also bounds UTF-16 to <=240 code units. Leave room
    # below common 255-byte/component limits, preserving the final extension.
    if len(name.encode('utf-8')) > 240:
        stem, dot, extension = name.rpartition('.')
        suffix = dot + extension if stem and dot else ''
        if len(suffix.encode('utf-8')) > 239:
            suffix = ''  # An extension alone can exceed filesystem limits.
        prefix = name[:-len(suffix)] if suffix else name
        budget = 240 - len(suffix.encode('utf-8'))
        prefix = prefix.encode('utf-8')[:budget].decode('utf-8', errors='ignore')
        name = (prefix or '_') + suffix
        name = name.rstrip(' .')
        # Truncation with a very long extension can itself create a device stem.
        stem = name.split('.', 1)[0].rstrip(' ').upper()
        if stem in {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'} or re.fullmatch(r'(COM|LPT)[1-9¹²³]', stem):
            name = '_' + name[1:]
    return name


class Transfer:
    """One file until clear(); batch additions are atomic."""

    def __init__(self):
        self.clear()

    def clear(self):
        self._metadata = None
        self._chunks = {}

    @property
    def total_parts(self):
        return self._metadata[5] if self._metadata else 0

    @property
    def received_parts(self):
        return len(self._chunks)

    @property
    def file_size(self):
        return self._metadata[3] if self._metadata else 0

    @property
    def missing(self):
        if self._metadata is None:
            return ()
        return tuple(i for i in range(1, self._metadata[5] + 1) if i not in self._chunks)

    @property
    def filename(self):
        return safe_filename(self._metadata[2]) if self._metadata else 'received-file'

    @property
    def status(self):
        if self._metadata is None:
            return '등록된 파일이 없습니다.'
        if self._metadata[0] == 'base64-transfer-v2':
            return '원본 크기와 SHA-256 검증 완료. 파일을 저장할 수 있습니다.'
        received = f'조각 {len(self._chunks)}/{self._metadata[5]}개 수신.'
        if self.missing:
            return received + ' 누락된 조각: ' + ', '.join(map(str, self.missing))
        return received + ' 크기 및 SHA-256 검증 완료. 저장할 수 있습니다.'

    @staticmethod
    def _assemble(metadata, chunks):
        raw = b''.join(chunks[i] for i in range(1, metadata[5] + 1))
        if len(raw) != metadata[3]:
            raise DecodeError('Assembled size mismatch.')
        if hashlib.sha256(raw).hexdigest() != metadata[4]:
            raise DecodeError('Assembled SHA-256 mismatch. Clear and recopy the file.')
        return raw

    def add(self, text):
        incoming = parse_envelopes(text)
        metadata = self._metadata or incoming[0].metadata
        chunks = dict(self._chunks)
        added = 0
        for chunk in incoming:
            if chunk.metadata != metadata:
                raise DecodeError('Conflicting metadata or mixed file IDs; Clear before a different file.')
            if chunk.part in chunks:
                if chunks[chunk.part] != chunk.raw:
                    raise DecodeError('Conflicting duplicate part.')
            else:
                chunks[chunk.part] = chunk.raw
                added += 1
        if len(chunks) == metadata[5]:
            self._assemble(metadata, chunks)
        self._metadata, self._chunks = metadata, chunks
        return added

    def assemble(self):
        if self._metadata is None or self.missing:
            raise DecodeError('Cannot save: no file or missing parts.')
        return self._assemble(self._metadata, self._chunks)
