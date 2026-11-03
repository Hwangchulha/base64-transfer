package app.base64transfer;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.zip.Deflater;

/** Pure JVM protocol implementation. Caller owns and closes the stream. */
public final class Transfer {
    public static final int LIMIT_BYTES = 1024 * 1024;
    public final String name;
    public final String sha256;
    public final int size;
    public final int parts;
    public final boolean compressed;
    /** Selected payload byte count: compressed size for v4, original size for v3. */
    public final int packedSize;
    private final String envelope;

    private Transfer(String name, byte[] bytes) throws IOException {
        this.name = boundedName(name);
        size = bytes.length;
        parts = 1;
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder hex = new StringBuilder(64);
            for (byte b : digest) hex.append(String.format(java.util.Locale.ROOT, "%02x", b & 255));
            sha256 = hex.toString();
        } catch (NoSuchAlgorithmException impossible) {
            throw new AssertionError(impossible);
        }
        byte[] packed = compress(bytes);
        String original = encodeEnvelope(bytes, false);
        String candidate = encodeEnvelope(packed, true);
        compressed = candidate.length() < original.length();
        packedSize = compressed ? packed.length : size;
        envelope = compressed ? candidate : original;
    }

    public static Transfer read(InputStream input, String name) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int count = 0;
        while (true) {
            if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Cancelled");
            // Read at most the limit, including the single byte proving rejection.
            int n = input.read(buffer, 0, Math.min(buffer.length, LIMIT_BYTES - count));
            if (n < 0) break;
            if (n == 0) {
                int b = input.read();
                if (b < 0) break;
                buffer[0] = (byte) b;
                n = 1;
            }
            count += n;
            if (count >= LIMIT_BYTES) throw new IOException("파일은 1 MiB(1,048,576바이트) 미만이어야 합니다.");
            out.write(buffer, 0, n);
        }
        return new Transfer(name, out.toByteArray());
    }

    public String envelope(int part) {
        if (part < 1 || part > parts) throw new IllegalArgumentException("Invalid part");
        return envelope;
    }

    private static byte[] compress(byte[] bytes) throws IOException {
        Deflater deflater = new Deflater(Deflater.DEFAULT_COMPRESSION, false);
        try {
            deflater.setInput(bytes);
            deflater.finish();
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            while (!deflater.finished()) {
                if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Cancelled");
                int count = deflater.deflate(buffer);
                if (count == 0 && !deflater.finished()) throw new IOException("Compression stalled");
                if (output.size() + count > LIMIT_BYTES + 65536) throw new IOException("Compression output limit");
                output.write(buffer, 0, count);
            }
            return output.toByteArray();
        } finally {
            deflater.end();
        }
    }

    private String encodeEnvelope(byte[] payload, boolean packed) {
        String data = CompactText15.encode(payload);
        return "{\"format\":\"text-transfer-" + (packed ? "v4" : "v3") + "\",\"id\":\"" + sha256
                + "\",\"name\":" + quote(name) + ",\"size\":" + size
                + ",\"sha256\":\"" + sha256 + "\",\"part\":1,\"parts\":1"
                + (packed ? ",\"encoding\":\"zlib\",\"packedSize\":" + payload.length : "")
                + ",\"data\":\"" + data + "\"}";
    }

    // Preserve the original name in the protocol up to 255 UTF-16 units.
    public static String boundedName(String name) {
        if (name == null || name.isEmpty()) return "unnamed";
        int end = Math.min(255, name.length());
        if (end < name.length() && Character.isHighSurrogate(name.charAt(end - 1))) end--;
        return name.substring(0, end);
    }

    public static String displayName(String name) {
        StringBuilder result = new StringBuilder();
        boundedName(name).codePoints().forEach(c -> result.appendCodePoint(
                Character.isISOControl(c) || Character.getType(c) == Character.FORMAT
                        || Character.getType(c) == Character.LINE_SEPARATOR
                        || Character.getType(c) == Character.PARAGRAPH_SEPARATOR
                        || Character.getType(c) == Character.SURROGATE ? 0xfffd : c));
        return result.toString();
    }

    private static String quote(String value) {
        StringBuilder out = new StringBuilder("\"");
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '"' || c == '\\') out.append('\\').append(c);
            else if (c < 32 || Character.isSurrogate(c))
                out.append(String.format(java.util.Locale.ROOT, "\\u%04x", (int) c));
            else out.append(c);
        }
        return out.append('"').toString();
    }
}
