package app.base64transfer;

/** v3: big-endian groups of 15 bits; the final group is zero-padded on the right. */
public final class CompactText15 {
    private CompactText15() { }

    public static char symbol(int index) {
        if (index < 0 || index >= 32768) throw new IllegalArgumentException("Invalid symbol index");
        if (index < 6582) return (char) (0x3400 + index);
        if (index < 27484) return (char) (0x4e00 + index - 6582);
        return (char) (0xac00 + index - 27484);
    }

    public static String encode(byte[] bytes) {
        long length = ((long) bytes.length * 8 + 14) / 15;
        if (length > Integer.MAX_VALUE) throw new IllegalArgumentException("Input too large");
        StringBuilder output = new StringBuilder((int) length);
        int pending = 0;
        int bits = 0;
        for (byte value : bytes) {
            pending = (pending << 8) | (value & 255);
            bits += 8;
            if (bits >= 15) {
                bits -= 15;
                output.append(symbol((pending >>> bits) & 32767));
                pending &= (1 << bits) - 1;
            }
        }
        if (bits != 0) output.append(symbol(pending << (15 - bits)));
        return output.toString();
    }
}
