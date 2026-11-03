package app.base64transfer;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Base64;

/** Pure JVM protocol implementation. Caller owns and closes the stream. */
public final class Transfer {
    public static final int LIMIT_BYTES = 1024 * 1024;
    public static final int CHUNK_BYTES = 100 * 1024;
    public final String name;
    public final String sha256;
    public final int size;
    public final int parts;
    private final String[] envelopes;

    private Transfer(String name, byte[] bytes) {
        this.name = boundedName(name);
        size = bytes.length;
        parts = Math.max(1, (size + CHUNK_BYTES - 1) / CHUNK_BYTES);
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder hex = new StringBuilder(64);
            for (byte b : digest) hex.append(String.format(java.util.Locale.ROOT, "%02x", b & 255));
            sha256 = hex.toString();
        } catch (NoSuchAlgorithmException impossible) {
            throw new AssertionError(impossible);
        }
        envelopes = new String[parts];
        for (int part = 1; part <= parts; part++) envelopes[part - 1] = encodeEnvelope(bytes, part);
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
        return envelopes[part - 1];
    }

    private String encodeEnvelope(byte[] bytes, int part) {
        int start = (part - 1) * CHUNK_BYTES;
        String data = Base64.getEncoder().encodeToString(Arrays.copyOfRange(bytes, start, Math.min(size, start + CHUNK_BYTES)));
        return "{\"format\":\"base64-transfer-v1\",\"id\":\"" + sha256
                + "\",\"name\":" + quote(name) + ",\"size\":" + size
                + ",\"sha256\":\"" + sha256 + "\",\"part\":" + part
                + ",\"parts\":" + parts + ",\"data\":\"" + data + "\"}";
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
