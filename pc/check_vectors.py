"""Validate Android-exported envelope text offline; optionally compare original bytes."""
import argparse
from pathlib import Path

from decoder import DecodeError, MAX_FILE_BYTES, MAX_TEXT_CHARS, Transfer


def load_vectors(paths, expected=None):
    transfer = Transfer()
    for path in paths:
        # UTF-8 can use four bytes per character. Bound reads before decoding.
        with Path(path).open('rb') as source:
            payload = source.read(MAX_TEXT_CHARS * 4 + 1)
        if len(payload) > MAX_TEXT_CHARS * 4:
            raise DecodeError('Vector text file exceeds input limit.')
        transfer.add(payload.decode('utf-8'))
    result = transfer.assemble()
    if expected is not None:
        with Path(expected).open('rb') as source:
            original = source.read(MAX_FILE_BYTES)
        if len(original) >= MAX_FILE_BYTES or original != result:
            raise DecodeError('Decoded bytes differ from the original file.')
    return transfer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('envelopes', nargs='+', help='UTF-8 files containing consecutive JSON envelopes')
    parser.add_argument('--expected', help='Optional original binary file to compare')
    args = parser.parse_args()
    try:
        transfer = load_vectors(args.envelopes, args.expected)
    except (OSError, UnicodeError, DecodeError) as exc:
        parser.exit(1, f'FAIL: {exc}\n')
    print('PASS:', transfer.status)


if __name__ == '__main__':
    main()
