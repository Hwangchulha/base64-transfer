import app.base64transfer.CompactText15;
import java.text.Normalizer;
import java.util.Arrays;
import java.util.Random;

public final class CompactText15Test {
    static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    static int index(char c) {
        if (c >= 0x3400 && c <= 0x4db5) return c - 0x3400;
        if (c >= 0x4e00 && c <= 0x9fa5) return 6582 + c - 0x4e00;
        if (c >= 0xac00 && c <= 0xc0a3) return 27484 + c - 0xac00;
        throw new AssertionError("Outside alphabet");
    }
    // Deliberately bit-by-bit reference decoder, independent of the encoder buffer.
    static byte[] decode(String text, int size) {
        check(text.length() == (size * 8L + 14) / 15, "symbol count");
        byte[] result = new byte[size];
        int bitPosition = 0;
        for (int i = 0; i < text.length(); i++) {
            int value = index(text.charAt(i));
            for (int bit = 14; bit >= 0; bit--, bitPosition++) {
                int one = (value >>> bit) & 1;
                if (bitPosition < size * 8) result[bitPosition / 8] |= one << (7 - bitPosition % 8);
                else check(one == 0, "nonzero right padding");
            }
        }
        return result;
    }
    public static void run() {
        StringBuilder alphabet = new StringBuilder();
        boolean[] seen = new boolean[65536];
        for (int i = 0; i < 32768; i++) {
            char c = CompactText15.symbol(i);
            check(index(c) == i && !seen[c], "alphabet mapping");
            check(!Character.isSurrogate(c) && Character.isDefined(c), "assigned BMP character");
            seen[c] = true;
            alphabet.append(c);
            byte[] pair = {(byte) (i >>> 7), (byte) (i << 1)};
            String encoded = CompactText15.encode(pair);
            check(encoded.charAt(0) == c && encoded.charAt(1) == 0x3400, "all indexes/highest index");
        }
        check(CompactText15.symbol(6581) == 0x4db5 && CompactText15.symbol(6582) == 0x4e00, "first boundary");
        check(CompactText15.symbol(27483) == 0x9fa5 && CompactText15.symbol(27484) == 0xac00
                && CompactText15.symbol(32767) == 0xc0a3, "second/last boundary");
        check(Normalizer.isNormalized(alphabet, Normalizer.Form.NFC), "NFC stability");
        check(Normalizer.isNormalized(alphabet, Normalizer.Form.NFKC), "NFKC stability");
        for (int size : new int[]{0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,700000,716800,1048575}) {
            byte[] input = new byte[size];
            new Random(0x15c0deL + size).nextBytes(input);
            check(Arrays.equals(input, decode(CompactText15.encode(input), size)), "random/padding roundtrip " + size);
        }
        check(CompactText15.encode(new byte[]{(byte)255}).charAt(0) == CompactText15.symbol(32640), "right padding known answer");
        System.out.println("PASS: compact15 all 32768 symbols, NFC/NFKC, alphabet edges, right padding, random 700000/716800 bytes");
    }
}
