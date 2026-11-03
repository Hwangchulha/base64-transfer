import app.base64transfer.Transfer;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public final class ProtocolTest {
    static byte[] payload(int size) {
        byte[] data = new byte[size];
        for (int i = 0; i < size; i++) data[i] = (byte) (i * 31 + 7);
        return data;
    }
    static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        if (args.length > 0 && args[0].equals("vectors")) {
            int size = args.length > 1 ? Integer.parseInt(args[1]) : 102401;
            if (size < 0 || size > Transfer.LIMIT_BYTES) throw new IllegalArgumentException("Invalid test size");
            boolean random = args.length > 2 && args[2].equals("random");
            byte[] input = payload(size);
            if (random) {
                int state = 0x15c0de;
                for (int i = 0; i < size; i++) {
                    state ^= state << 13;
                    state ^= state >>> 17;
                    state ^= state << 5;
                    input[i] = (byte) state;
                }
            }
            Transfer transfer = Transfer.read(new ByteArrayInputStream(input), (random ? "random-vector-" : "vector-") + size + ".bin");
            for (int p = 1; p <= transfer.parts; p++) System.out.println(transfer.envelope(p));
            return;
        }
        for (int size : new int[]{0, 1, 2, 3, 102399, 102400, 102401, 700000, 716800, 1048575}) {
            byte[] raw = payload(size);
            // Provider can return short reads and report misleading available().
            InputStream shortReads = new ByteArrayInputStream(raw) {
                @Override public synchronized int read(byte[] b, int off, int n) { return super.read(b, off, Math.min(n, 17)); }
                @Override public synchronized int available() { return Integer.MAX_VALUE; }
            };
            Transfer t = Transfer.read(shortReads, "original.bin");
            check(t.size == size && t.parts == 1, "size/parts");
            ByteArrayOutputStream joined = new ByteArrayOutputStream();
            for (int p = 1; p <= t.parts; p++) {
                String json = t.envelope(p);
                String encoded = json.substring(json.indexOf("\"data\":\"") + 8, json.length() - 2);
                byte[] chunk = CompactText15Test.decode(encoded, size);
                check(chunk.length == size, "full single payload");
                check(json.startsWith("{\"format\":\"text-transfer-v3\""), "v3 format");
                joined.write(chunk);
            }
            check(Arrays.equals(raw, joined.toByteArray()), "roundtrip " + size);
            try { t.envelope(0); throw new AssertionError("part zero accepted"); } catch (IllegalArgumentException expected) { }
            try { t.envelope(t.parts + 1); throw new AssertionError("excess part accepted"); } catch (IllegalArgumentException expected) { }
        }
        CompactText15Test.run();
        final int[] consumed = {0};
        InputStream endless = new InputStream() {
            @Override public int read() { consumed[0]++; return 7; }
            @Override public int read(byte[] b, int off, int n) { consumed[0] += n; Arrays.fill(b, off, off + n, (byte) 7); return n; }
        };
        try { Transfer.read(endless, "large"); throw new AssertionError("limit accepted"); }
        catch (IOException expected) { check(consumed[0] == 1048576, "read exceeded cap"); }
        try { Transfer.read(new ByteArrayInputStream(payload(1048576)), "exact"); throw new AssertionError("exact cap accepted"); }
        catch (IOException expected) { }
        Transfer empty = Transfer.read(new ByteArrayInputStream(new byte[0]), "empty");
        check(empty.sha256.equals("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"), "empty digest");
        Transfer abc = Transfer.read(new ByteArrayInputStream("abc".getBytes(StandardCharsets.UTF_8)), "a\"\\\n.txt");
        check(abc.sha256.equals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"), "abc digest");
        check(abc.envelope(1).contains("a\\\"\\\\\\u000a.txt"), "JSON escaping");
        check(Transfer.boundedName("a".repeat(254) + "😀").length() == 254, "split surrogate");
        check(!Transfer.displayName("a\n\u202eb").contains("\u202e"), "unsafe display");
        InputStream zeros = new ByteArrayInputStream(new byte[]{4}) {
            @Override public int read(byte[] b, int off, int n) { return 0; }
        };
        check(Transfer.read(zeros, "zero reads").size == 1, "zero read fallback");
        Thread.currentThread().interrupt();
        try { Transfer.read(new ByteArrayInputStream(new byte[0]), "cancel"); throw new AssertionError("not cancelled"); }
        catch (InterruptedIOException expected) { Thread.interrupted(); }
        System.out.println("PASS: boundaries, single-full roundtrip, digest, bounded stream, escaping, cancellation");
    }
}
