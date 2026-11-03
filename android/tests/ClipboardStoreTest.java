import app.base64transfer.ClipboardStore;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;

public final class ClipboardStoreTest {
    interface Operation { void run() throws Exception; }
    static void rejected(Operation operation) throws Exception {
        try { operation.run(); throw new AssertionError("Accepted invalid request"); }
        catch (IOException expected) { }
    }
    public static void main(String[] args) throws Exception {
        Path cache = Files.createTempDirectory(Path.of(args[0]), "clipboard-test-");
        try {
            String text = "본문\n" + "a".repeat(1398100);
            String uri = ClipboardStore.write(cache.toFile(), text);
            Path saved = ClipboardStore.resolve(cache.toFile(), uri).toPath();
            if (!Files.readString(saved, StandardCharsets.UTF_8).equals(text)) throw new AssertionError("Stream mismatch");
            String[] bad = {uri + "/", uri + "?query=x", uri + "#fragment", uri.replace("content:", "file:"),
                    uri.replace("/text/", "/text/../"), uri.replace("/text/", "/text/%2e%2e/"),
                    uri.replace("clipboard/", "clipboard.evil/"), uri.replace("content://", "content://user@"),
                    uri.toUpperCase(), "content://app.base64transfer.clipboard/text/../../secret"};
            for (String value : bad) rejected(() -> ClipboardStore.resolve(cache.toFile(), value));
            rejected(() -> ClipboardStore.write(cache.toFile(), "a".repeat(1500001)));
            Files.delete(saved);
            rejected(() -> ClipboardStore.resolve(cache.toFile(), uri));
            Path other = cache.resolve("private-file");
            Files.writeString(other, "private");
            Files.createSymbolicLink(saved, other);
            rejected(() -> ClipboardStore.resolve(cache.toFile(), uri));
            Files.delete(saved);
            for (int i = 0; i < 20; i++) ClipboardStore.write(cache.toFile(), "data");
            try (var entries = Files.list(cache.resolve("text-clips"))) {
                if (entries.count() > 16) throw new AssertionError("Unbounded cache");
            }
            System.out.println("PASS: text cache roundtrip, exact URI validation, traversal, symlink, missing files, size and retention bounds");
        } finally {
            try (var files = Files.walk(cache)) {
                for (Path file : files.sorted(java.util.Comparator.reverseOrder()).toList()) Files.delete(file);
            }
        }
    }
}
