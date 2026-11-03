import app.base64transfer.Transfer;
import app.base64transfer.CompactText15;
import java.io.*;
import java.util.*;
import java.util.zip.*;

public final class CompressionTest {
    static byte[] unpack(byte[] packed, int size) throws Exception {
        Inflater inflater = new Inflater(false);
        try {
            inflater.setInput(packed);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            while (!inflater.finished()) {
                int n = inflater.inflate(buffer);
                if (n == 0 && !inflater.finished()) throw new AssertionError("Incomplete zlib stream");
                out.write(buffer, 0, n);
                ProtocolTest.check(out.size() <= size, "bounded decompression");
            }
            ProtocolTest.check(inflater.getRemaining() == 0 && out.size() == size, "strict zlib completion");
            return out.toByteArray();
        } finally { inflater.end(); }
    }

    static void verify(byte[] raw, Boolean expectedCompressed) throws Exception {
        Transfer t = Transfer.read(new ByteArrayInputStream(raw), "test.bin");
        ByteArrayOutputStream compressed = new ByteArrayOutputStream();
        try (DeflaterOutputStream stream = new DeflaterOutputStream(compressed)) { stream.write(raw); }
        byte[] packed = compressed.toByteArray();
        String prefix = "{\"format\":\"text-transfer-v3\",\"id\":\"" + t.sha256
                + "\",\"name\":\"test.bin\",\"size\":" + raw.length + ",\"sha256\":\"" + t.sha256
                + "\",\"part\":1,\"parts\":1";
        String original = prefix + ",\"data\":\"" + CompactText15.encode(raw) + "\"}";
        String candidate = prefix.replace("text-transfer-v3", "text-transfer-v4")
                + ",\"encoding\":\"zlib\",\"packedSize\":" + packed.length
                + ",\"data\":\"" + CompactText15.encode(packed) + "\"}";
        ProtocolTest.check(t.compressed == (candidate.length() < original.length()), "full envelope comparison");
        ProtocolTest.check(t.envelope(1).equals(t.compressed ? candidate : original), "exact selected envelope");
        ProtocolTest.check(t.packedSize == (t.compressed ? packed.length : raw.length), "packedSize");
        if (expectedCompressed != null) ProtocolTest.check(t.compressed == expectedCompressed, "expected format");
        String json = t.envelope(1);
        String data = json.substring(json.indexOf("\"data\":\"") + 8, json.length() - 2);
        byte[] decoded = CompactText15Test.decode(data, t.packedSize);
        if (t.compressed) decoded = unpack(decoded, t.size);
        ProtocolTest.check(Arrays.equals(decoded, raw), "lossless compression roundtrip");
    }

    public static void run() throws Exception {
        verify(new byte[0], false);
        verify(new byte[]{1,2,3}, false);
        for (int size = 1; size <= 180; size++) verify(new byte[size], null);
        for (int size : new int[]{700000, 716800}) {
            verify(new byte[size], true);
            byte[] random = new byte[size];
            new Random(size).nextBytes(random);
            verify(random, false);
        }
        System.out.println("PASS: wrapped zlib/Inflater roundtrip, full-envelope selection, small/empty, compressible and random 700 KiB");
    }
}
