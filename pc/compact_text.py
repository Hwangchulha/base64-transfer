"""15 bits per printable BMP character; this is encoding, not encryption."""


def symbol_value(character):
    point = ord(character)
    if 0x3400 <= point <= 0x4DB5:
        return point - 0x3400
    if 0x4E00 <= point <= 0x9FA5:
        return point - 0x4E00 + 6582
    if 0xAC00 <= point <= 0xC0A3:
        return point - 0xAC00 + 27484
    raise ValueError('Compact text contains an unsupported character.')


def decode_compact(data, size):
    if len(data) != (size * 8 + 14) // 15:
        raise ValueError('Compact text length does not match the original file size.')
    result = bytearray()
    accumulator = bits = 0
    for character in data:
        accumulator = (accumulator << 15) | symbol_value(character)
        bits += 15
        while bits >= 8 and len(result) < size:
            bits -= 8
            result.append((accumulator >> bits) & 255)
        accumulator &= (1 << bits) - 1
    if len(result) != size or bits != len(data) * 15 - size * 8 or accumulator:
        raise ValueError('Compact text has invalid trailing padding.')
    return bytes(result)
