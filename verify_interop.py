"""Run real Android Java encoder against PC Python decoder, without a device."""
import hashlib
import json
import pathlib
import random
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pc'))
from decoder import Transfer, CHUNK_BYTES, MAX_FILE_BYTES
from encoder import encode_bytes

JDK = ROOT.parent / 'personal-ledger/.tools/jdk/bin'
JAVA_SOURCE = r'''
import app.base64transfer.Transfer;
import java.io.FileInputStream;
public class Interop {
    public static void main(String[] args) throws Exception {
        try (FileInputStream input = new FileInputStream(args[0])) {
            Transfer transfer = Transfer.read(input, "보고서_사진_😀.xlsx");
            for (int part = transfer.parts; part >= 1; part--)
                System.out.println(transfer.envelope(part));
        }
    }
}
'''


def main():
    with tempfile.TemporaryDirectory() as folder:
        temp = pathlib.Path(folder)
        source = temp / 'Interop.java'
        source.write_text(JAVA_SOURCE, encoding='utf-8')
        subprocess.run([str(JDK / 'javac'), '-encoding', 'UTF-8', '-d', folder,
                        str(ROOT / 'android/app/src/main/java/app/base64transfer/Transfer.java'),
                        str(ROOT / 'android/app/src/main/java/app/base64transfer/CompactText15.java'),
                        str(source)], check=True)
        sizes = [0, 1, 2, 3, CHUNK_BYTES-1, CHUNK_BYTES, CHUNK_BYTES+1, 700000, 716800, MAX_FILE_BYTES-1]
        cases = [(str(size), bytes(range(256)) * (size // 256) + bytes(range(size % 256))) for size in sizes]
        cases.append(("random700KiB", random.Random(42).randbytes(716800)))
        for label, data in cases:
            size = len(data)
            input_path = temp / 'input.bin'
            input_path.write_bytes(data)
            output = subprocess.check_output([str(JDK / 'java'), '-cp', folder, 'Interop', str(input_path)],
                                             encoding='utf-8')
            transfer = Transfer()
            lines = output.splitlines()
            assert len(lines) == 1, 'A file must not be split'
            obj = json.loads(lines[0])
            expected = 'text-transfer-v4' if size > 1000 and label != 'random700KiB' else 'text-transfer-v3'
            assert obj['format'] == expected, (label, obj['format'])
            pc_body = encode_bytes(data, '보고서_사진_😀.xlsx')
            pc_obj = json.loads(pc_body)
            assert pc_obj['format'] == obj['format']
            for field in ('id', 'name', 'size', 'sha256', 'part', 'parts'):
                assert pc_obj[field] == obj[field], (label, field)
            if expected == 'text-transfer-v3':
                assert pc_obj['data'] == obj['data'], 'PC/Android compact encoding differs'
            pc_transfer = Transfer()
            pc_transfer.add(pc_body)
            assert pc_transfer.assemble() == data
            if size == 716800:
                assert len(lines[0].encode('utf-16-le')) < 800 * 1024
                print('700KiB UTF16 payload bytes:', len(lines[0].encode('utf-16-le')))
            for line in lines:
                transfer.add(line)
            assert transfer.add(lines[0]) == 0, 'Duplicate was not ignored'
            assert transfer.assemble() == data
            assert transfer.filename == '보고서_사진_😀.xlsx'
            assert not transfer.missing
            print(f'PASS {label}: {size} bytes, {len(lines)} part(s), reverse order + duplicate, '
                  f'SHA256 {hashlib.sha256(data).hexdigest()[:12]}')
        input_path.write_bytes(bytes(MAX_FILE_BYTES))
        rejected = subprocess.run([str(JDK / 'java'), '-cp', folder, 'Interop', str(input_path)],
                                  capture_output=True)
        assert rejected.returncode != 0 and b'java.io.IOException' in rejected.stderr and b'1,048,576' in rejected.stderr
        print('PASS exact 1 MiB rejected by Java encoder')


if __name__ == '__main__':
    main()
