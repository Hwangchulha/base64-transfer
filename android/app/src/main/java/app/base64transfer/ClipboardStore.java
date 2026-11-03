package app.base64transfer;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;
import java.util.Comparator;
import java.util.UUID;
import java.util.regex.Pattern;

/** Private, bounded text cache. No caller-supplied paths or original filenames. */
public final class ClipboardStore {
    public static final String AUTHORITY = "app.base64transfer.clipboard";
    private static final String PREFIX = "content://" + AUTHORITY + "/text/";
    private static final Pattern TOKEN = Pattern.compile("[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}");
    public static final int MAX_TEXT_BYTES = 1500000;
    private static final long MAX_AGE_MS = 24L * 60 * 60 * 1000;

    public static String token(String uri) throws IOException {
        if (uri == null || !uri.startsWith(PREFIX)) throw unavailable();
        String token = uri.substring(PREFIX.length());
        if (!TOKEN.matcher(token).matches()) throw unavailable();
        return token;
    }

    private static File directory(File cache) throws IOException {
        File dir = new File(cache, "text-clips");
        if (Files.isSymbolicLink(dir.toPath())) throw unavailable();
        if (!dir.isDirectory() && !dir.mkdir()) throw unavailable();
        return dir.getCanonicalFile();
    }

    public static synchronized String write(File cache, String text) throws IOException {
        byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_TEXT_BYTES) throw new IOException("Text exceeds cache budget");
        File dir = directory(cache);
        File[] existing = dir.listFiles(f -> TOKEN.matcher(f.getName()).matches());
        if (existing != null) {
            Arrays.sort(existing, Comparator.comparingLong(File::lastModified));
            for (int i = 0; i < existing.length; i++) {
                if (i < existing.length - 15 || System.currentTimeMillis() - existing[i].lastModified() > MAX_AGE_MS)
                    Files.deleteIfExists(existing[i].toPath());
            }
        }
        String token = UUID.randomUUID().toString();
        File file = new File(dir, token);
        // CREATE_NEW prevents replacing an existing file or following a pre-existing symlink.
        try {
            Files.write(file.toPath(), bytes, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
        } catch (IOException failure) {
            Files.deleteIfExists(file.toPath());
            throw new IOException("Cannot prepare clipboard text");
        }
        return PREFIX + token;
    }

    public static File resolve(File cache, String uri) throws IOException {
        String token = token(uri);
        File dir = directory(cache);
        File file = new File(dir, token);
        if (Files.isSymbolicLink(file.toPath()) || !file.getCanonicalFile().getParentFile().equals(dir)
                || !file.isFile() || file.length() > MAX_TEXT_BYTES
                || System.currentTimeMillis() - file.lastModified() > MAX_AGE_MS) throw unavailable();
        return file;
    }

    private static IOException unavailable() { return new IOException("Clipboard text unavailable; copy again"); }
}
