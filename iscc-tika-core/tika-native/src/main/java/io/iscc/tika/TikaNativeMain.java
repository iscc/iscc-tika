package io.iscc.tika;

import org.apache.commons.compress.archivers.zip.ZipArchiveEntry;
import org.apache.commons.io.input.ReaderInputStream;
import org.apache.tika.Tika;
import org.apache.tika.config.TikaConfig;
import org.apache.tika.exception.EncryptedDocumentException;
import org.apache.tika.exception.TikaException;
import org.apache.tika.exception.WriteLimitReachedException;
import org.apache.tika.io.TemporaryResources;
import org.apache.tika.io.TikaInputStream;
import org.apache.tika.metadata.Metadata;
import org.apache.tika.metadata.TikaCoreProperties;
import org.apache.tika.parser.AutoDetectParser;
import org.apache.tika.parser.ParseContext;
import org.apache.tika.parser.Parser;
import org.apache.tika.parser.microsoft.OfficeParserConfig;
import org.apache.tika.parser.ocr.TesseractOCRConfig;
import org.apache.tika.parser.pdf.PDFParserConfig;
import org.apache.tika.sax.BodyContentHandler;
import org.apache.tika.sax.EmbeddedContentHandler;
import org.apache.tika.sax.ToXMLContentHandler;
import org.apache.tika.sax.WriteOutContentHandler;
import org.graalvm.nativeimage.IsolateThread;
import org.graalvm.nativeimage.c.function.CEntryPoint;
import org.graalvm.nativeimage.c.type.CCharPointer;
import org.graalvm.nativeimage.c.type.CConst;
import org.graalvm.nativeimage.c.type.CTypeConversion;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.ContentHandler;
import org.xml.sax.SAXException;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.Reader;
import java.net.MalformedURLException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URL;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.InvalidPathException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class TikaNativeMain {

    private static final Tika tika = new Tika();

    /**
     * Parses the given file and returns its type as a mime type
     *
     * @param filePath: the path of the file to be parsed
     * @return StringResult
     */
    public static StringResult detect(String filePath) {
        final Path path = Paths.get(filePath);
        final Metadata metadata = new Metadata();

        try (final InputStream stream = TikaInputStream.get(path, metadata)) {
            final String result = tika.detect(stream, metadata);
            return new StringResult(result, metadata);

        } catch (java.io.IOException e) {
            return new StringResult((byte) 1, e.getMessage());
        }
    }

    /**
     * Parses the given file and returns its content as String.
     * To avoid unpredictable excess memory use, the returned string contains only up to maxLength
     * first characters extracted from the input document.
     *
     * @param filePath:  the path of the file to be parsed
     * @param maxLength: maximum length of the returned string
     * @return StringResult
     */
    public static StringResult parseFileToString(
            String filePath,
            int maxLength,
            PDFParserConfig pdfConfig,
            OfficeParserConfig officeConfig,
            TesseractOCRConfig tesseractConfig,
            boolean asXML
            // maybe replace with a single config class
    ) {
        try {
            final Path path = Paths.get(filePath);
            final Metadata metadata = new Metadata();

            String result;
            try {
                final InputStream stream = TikaInputStream.get(path, metadata);
                result = parseToStringWithConfig(
                        stream, metadata, maxLength, pdfConfig, officeConfig, tesseractConfig, asXML);
                // No need to close the stream because parseToString does so
            } catch (TikaException e) {
                if (!isEpubTika198(e)) {
                    throw e;
                }
                metadata.add("X-TIKA:warning",
                        "EpubParser strict check failed; used lenient fallback: " + rootMessage(e));
                result = lenientEpubParseToString(
                        path, metadata, maxLength, pdfConfig, officeConfig, tesseractConfig, asXML);
            }

            return new StringResult(result, metadata);
        } catch (java.io.IOException e) {
            return new StringResult((byte) 1, "Could not open file: " + e.getMessage());
        } catch (TikaException e) {
            return new StringResult((byte) 2, "Parse error occurred : " + e.getMessage());
        }
    }

    /**
     * Parses the given Url and returns its content as String
     *
     * @param urlString the url to be parsed
     * @return StringResult
     */
    public static StringResult parseUrlToString(
            String urlString,
            int maxLength,
            PDFParserConfig pdfConfig,
            OfficeParserConfig officeConfig,
            TesseractOCRConfig tesseractConfig,
            boolean asXML
    ) {
        try {
            final URL url = new URI(urlString).toURL();
            final Metadata metadata = new Metadata();
            final TikaInputStream stream = TikaInputStream.get(url, metadata);

            String result = parseToStringWithConfig(
                    stream, metadata, maxLength, pdfConfig, officeConfig, tesseractConfig, asXML);
            // No need to close the stream because parseToString does so
            return new StringResult(result, metadata);

        } catch (MalformedURLException e) {
            return new StringResult((byte) 2, "Malformed URL error occurred " + e.getMessage());
        } catch (URISyntaxException e) {
            return new StringResult((byte) 2, "Malformed URI error occurred: " + e.getMessage());
        } catch (java.io.IOException e) {
            return new StringResult((byte) 1, "IO error occurred: " + e.getMessage());
        } catch (TikaException e) {
            return new StringResult((byte) 2, "Parse error occurred : " + e.getMessage());
        }
    }

    /**
     * Parses the given array of bytes and return its content as String.
     *
     * @param data an array of bytes
     * @return StringResult
     */
    public static StringResult parseBytesToString(
            ByteBuffer data,
            int maxLength,
            PDFParserConfig pdfConfig,
            OfficeParserConfig officeConfig,
            TesseractOCRConfig tesseractConfig,
            boolean asXML
    ) {
        final Metadata metadata = new Metadata();
        final ByteBufferInputStream inStream = new ByteBufferInputStream(data);
        final TikaInputStream stream = TikaInputStream.get(inStream, new TemporaryResources(), metadata);

        try {
            String result = parseToStringWithConfig(
                    stream, metadata, maxLength, pdfConfig, officeConfig, tesseractConfig, asXML);
            // No need to close the stream because parseToString does so
            return new StringResult(result, metadata);
        } catch (java.io.IOException e) {
            return new StringResult((byte) 1, "IO error occurred: " + e.getMessage());
        } catch (TikaException e) {
            if (!isEpubTika198(e)) {
                return new StringResult((byte) 2, "Parse error occurred : " + e.getMessage());
            }
            // Lenient fallback: dump bytes to a temp file and retry via path-based helper
            try {
                Path tmp = dumpToTempFile(data);
                try {
                    metadata.add("X-TIKA:warning",
                            "EpubParser strict check failed; used lenient fallback: " + rootMessage(e));
                    String result = lenientEpubParseToString(
                            tmp, metadata, maxLength, pdfConfig, officeConfig, tesseractConfig, asXML);
                    return new StringResult(result, metadata);
                } finally {
                    try { Files.deleteIfExists(tmp); } catch (IOException ignored) { }
                }
            } catch (IOException ioe) {
                return new StringResult((byte) 1, "IO error in EPUB fallback: " + ioe.getMessage());
            } catch (TikaException te) {
                return new StringResult((byte) 2, "EPUB fallback failed: " + te.getMessage());
            }
        }
    }

    private static String parseToStringWithConfig(
            InputStream stream,
            Metadata metadata,
            int maxLength,
            PDFParserConfig pdfConfig,
            OfficeParserConfig officeConfig,
            TesseractOCRConfig tesseractConfig,
            boolean asXML
    ) throws IOException, TikaException {
        ContentHandler handler;
        ContentHandler handlerForParser;
        if (asXML) {
            handler = new WriteOutContentHandler(new ToXMLContentHandler(), maxLength);
            handlerForParser = handler;
        } else {
            handler = new WriteOutContentHandler(maxLength);
            handlerForParser = new BodyContentHandler(handler);
        }

        try {
            final TikaConfig config = TikaConfig.getDefaultConfig();
            final ParseContext parsecontext = new ParseContext();
            final Parser parser = new AutoDetectParser(config);

            parsecontext.set(Parser.class, parser);
            parsecontext.set(PDFParserConfig.class, pdfConfig);
            parsecontext.set(OfficeParserConfig.class, officeConfig);
            parsecontext.set(TesseractOCRConfig.class, tesseractConfig);

            parser.parse(stream, handlerForParser, metadata, parsecontext);
        } catch (EncryptedDocumentException e) {
            // Document contains encrypted items (e.g. DRM-protected fonts in EPUBs).
            // Return whatever content was extracted before the exception and add a warning.
            metadata.add("X-TIKA:warning", "EncryptedDocumentException: " + e.getMessage());
        } catch (SAXException e) {
            if (!WriteLimitReachedException.isWriteLimitReached(e)) {
                // This should never happen with BodyContentHandler...
                throw new TikaException("Unexpected SAX processing failure", e);
            }
        } finally {
            stream.close();
        }
        return handler.toString();
    }


    /**
     * Parses the given file and returns its content as Reader. The reader can be used
     * to read chunks and must be closed when reading is finished
     *
     * @param filePath the path of the file
     * @return ReaderResult
     */
    public static ReaderResult parseFile(
            String filePath,
            String charsetName,
            PDFParserConfig pdfConfig,
            OfficeParserConfig officeConfig,
            TesseractOCRConfig tesseractConfig,
            boolean asXML
    ) {
        try {
//            System.out.println("pdfConfig.isExtractInlineImages = " + pdfConfig.isExtractInlineImages());
//            System.out.println("pdfConfig.isExtractMarkedContent = " + pdfConfig.isExtractMarkedContent());
//            System.out.println("pdfConfig.getOcrStrategy = " + pdfConfig.getOcrStrategy());
//            System.out.println("officeConfig.isIncludeHeadersAndFooters = " + officeConfig.isIncludeHeadersAndFooters());
//            System.out.println("officeConfig.isIncludeShapeBasedContent = " + officeConfig.isIncludeShapeBasedContent());
//            System.out.println("ocrConfig.getTimeoutSeconds = " + tesseractConfig.getTimeoutSeconds());
//            System.out.println("ocrConfig.language = " + tesseractConfig.getLanguage());

            final Path path = Paths.get(filePath);
            final Metadata metadata = new Metadata();
            final TikaInputStream stream = TikaInputStream.get(path, metadata);

            return parse(stream, metadata, charsetName, pdfConfig, officeConfig, tesseractConfig, asXML);

        } catch (java.io.IOException e) {
            return new ReaderResult((byte) 1, "Could not open file: " + e.getMessage());
        }
    }

    /**
     * Parses the given Url and returns its content as Reader. The reader can be used
     * to read chunks and must be closed when reading is finished
     *
     * @param urlString the url to be parsed
     * @return ReaderResult
     */
    public static ReaderResult parseUrl(
            String urlString,
            String charsetName,
            PDFParserConfig pdfConfig,
            OfficeParserConfig officeConfig,
            TesseractOCRConfig tesseractConfig,
            boolean asXML
    ) {
        try {
            final URL url = new URI(urlString).toURL();
            final Metadata metadata = new Metadata();
            final TikaInputStream stream = TikaInputStream.get(url, metadata);

            return parse(stream, metadata, charsetName, pdfConfig, officeConfig, tesseractConfig, asXML);

        } catch (MalformedURLException e) {
            return new ReaderResult((byte) 2, "Malformed URL error occurred " + e.getMessage());
        } catch (URISyntaxException e) {
            return new ReaderResult((byte) 3, "Malformed URI error occurred: " + e.getMessage());
        } catch (java.io.IOException e) {
            return new ReaderResult((byte) 1, "IO error occurred: " + e.getMessage());
        }
    }

    /**
     * Parses the given array of bytes and return its content as Reader. The reader can be used
     * to read chunks and must be closed when reading is finished
     *
     * @param data an array of bytes
     * @return ReaderResult
     */
    public static ReaderResult parseBytes(
            ByteBuffer data,
            String charsetName,
            PDFParserConfig pdfConfig,
            OfficeParserConfig officeConfig,
            TesseractOCRConfig tesseractConfig,
            boolean asXML
    ) {


        final Metadata metadata = new Metadata();
        final ByteBufferInputStream inStream = new ByteBufferInputStream(data);
        final TikaInputStream stream = TikaInputStream.get(inStream, new TemporaryResources(), metadata);

        return parse(stream, metadata, charsetName, pdfConfig, officeConfig, tesseractConfig, asXML);
    }

    private static ReaderResult parse(
            TikaInputStream inputStream,
            Metadata metadata,
            String charsetName,
            PDFParserConfig pdfConfig,
            OfficeParserConfig officeConfig,
            TesseractOCRConfig tesseractConfig,
            boolean asXML
    ) {
        try {

            final TikaConfig config = TikaConfig.getDefaultConfig();
            final ParseContext parsecontext = new ParseContext();
            final Parser parser = new AutoDetectParser(config);
            final Charset charset = Charset.forName(charsetName, StandardCharsets.UTF_8);

            parsecontext.set(Parser.class, parser);
            parsecontext.set(PDFParserConfig.class, pdfConfig);
            parsecontext.set(OfficeParserConfig.class, officeConfig);
            parsecontext.set(TesseractOCRConfig.class, tesseractConfig);

            //final Reader reader = new org.apache.tika.parser.ParsingReader(parser, inputStream, metadata, parsecontext);
            final Reader reader = new ParsingReader(parser, inputStream, metadata, parsecontext, asXML, charset.name());

            // Convert Reader which works with chars to ReaderInputStream which works with bytes
            ReaderInputStream readerInputStream = ReaderInputStream.builder()
                    .setReader(reader)
                    .setCharset(charset)
                    .get();

            return new ReaderResult(readerInputStream, metadata);

        } catch (java.io.IOException e) {
            return new ReaderResult((byte) 1, "IO error occurred: " + e.getMessage());
        }

    }

    /**
     * Detects the Tika "TIKA-198: Illegal IOException from EpubParser" wrapper, which
     * Tika 3.3.0 raises when EpubParser's strict content-item check fails — most commonly
     * because an OPF manifest href contains a ".." path traversal that zipFile.getEntry
     * cannot resolve (no path normalization). The enclosing method retries via
     * {@link #lenientEpubParseToString}.
     */
    private static boolean isEpubTika198(TikaException e) {
        String msg = e.getMessage();
        return msg != null && msg.contains("TIKA-198") && msg.contains("EpubParser");
    }

    /** Walks the cause chain and returns the deepest non-empty message, or the class name. */
    private static String rootMessage(Throwable t) {
        Throwable cur = t;
        Throwable deepest = t;
        while (cur != null) {
            deepest = cur;
            cur = cur.getCause();
        }
        String m = deepest.getMessage();
        return (m == null || m.isEmpty()) ? deepest.getClass().getSimpleName() : m;
    }

    /** Dumps a ByteBuffer's payload to a temp file so path-based parsing can retry from disk. */
    private static Path dumpToTempFile(ByteBuffer data) throws IOException {
        Path tmp = Files.createTempFile("iscc-tika-epub-", ".epub");
        ByteBuffer view = data.duplicate();
        view.rewind();
        try (FileChannel ch = FileChannel.open(tmp, StandardOpenOption.WRITE)) {
            while (view.hasRemaining()) {
                ch.write(view);
            }
        }
        return tmp;
    }

    /**
     * Lenient EPUB fallback: opens the zip directly via commons-compress, reads the OPF
     * manifest and spine, then feeds each referenced content document to AutoDetectParser
     * one at a time. Normalizes "../" path traversals so entries like "OEBPS/../toc.xhtml"
     * resolve to "toc.xhtml". Individual entry failures are recorded as warnings but do
     * not abort the overall parse. Used only when Tika's stock EpubParser fails with
     * TIKA-198 from an EpubZipException.
     */
    private static String lenientEpubParseToString(
            Path path,
            Metadata metadata,
            int maxLength,
            PDFParserConfig pdfConfig,
            OfficeParserConfig officeConfig,
            TesseractOCRConfig tesseractConfig,
            boolean asXML
    ) throws IOException, TikaException {
        ContentHandler handler;
        ContentHandler handlerForParser;
        if (asXML) {
            handler = new WriteOutContentHandler(new ToXMLContentHandler(), maxLength);
            handlerForParser = handler;
        } else {
            handler = new WriteOutContentHandler(maxLength);
            handlerForParser = new BodyContentHandler(handler);
        }

        final TikaConfig config = TikaConfig.getDefaultConfig();
        final Parser parser = new AutoDetectParser(config);
        final ParseContext ctx = new ParseContext();
        ctx.set(Parser.class, parser);
        ctx.set(PDFParserConfig.class, pdfConfig);
        ctx.set(OfficeParserConfig.class, officeConfig);
        ctx.set(TesseractOCRConfig.class, tesseractConfig);

        File file = path.toFile();
        try (org.apache.commons.compress.archivers.zip.ZipFile zf =
                     org.apache.commons.compress.archivers.zip.ZipFile.builder()
                             .setFile(file)
                             .get()) {
            EpubOpfInfo opf = readEpubOpf(zf, metadata);
            if (opf == null) {
                throw new TikaException("EPUB fallback: container.xml or OPF not found");
            }
            if (metadata.get(Metadata.CONTENT_TYPE) == null) {
                metadata.set(Metadata.CONTENT_TYPE, "application/epub+zip");
            }

            for (String href : opf.spineHrefs) {
                String entryPath = resolveEpubEntryPath(opf.opfDir, href);
                ZipArchiveEntry entry = zf.getEntry(entryPath);
                if (entry == null || !zf.canReadEntryData(entry)) {
                    metadata.add("X-TIKA:warning",
                            "EPUB fallback: missing or unreadable entry " + entryPath);
                    continue;
                }
                Metadata itemMeta = new Metadata();
                itemMeta.set(TikaCoreProperties.RESOURCE_NAME_KEY, entryPath);
                ContentHandler nested = new EmbeddedContentHandler(handlerForParser);
                try (InputStream is = zf.getInputStream(entry)) {
                    parser.parse(is, nested, itemMeta, ctx);
                } catch (SAXException sx) {
                    if (WriteLimitReachedException.isWriteLimitReached(sx)) {
                        break;
                    }
                    metadata.add("X-TIKA:warning",
                            "EPUB fallback: SAX error on " + entryPath + ": " + sx.getMessage());
                } catch (EncryptedDocumentException ex) {
                    metadata.add("X-TIKA:warning",
                            "EPUB fallback: encrypted entry " + entryPath + ": " + ex.getMessage());
                } catch (TikaException | IOException ex) {
                    metadata.add("X-TIKA:warning",
                            "EPUB fallback: failed on " + entryPath + ": " + ex.getMessage());
                }
            }
        }
        return handler.toString();
    }

    /** Resolves an OPF href against its parent directory, collapsing ".." segments. */
    private static String resolveEpubEntryPath(String opfDir, String href) {
        String combined = opfDir + href;
        try {
            String normalized = Paths.get(combined).normalize().toString().replace('\\', '/');
            // Strip leading "./" or "/" that some zips do not store
            while (normalized.startsWith("./")) {
                normalized = normalized.substring(2);
            }
            while (normalized.startsWith("/")) {
                normalized = normalized.substring(1);
            }
            return normalized;
        } catch (InvalidPathException ex) {
            return combined;
        }
    }

    /** Holds OPF state needed for lenient EPUB reassembly. */
    private static final class EpubOpfInfo {
        String opfDir = "";
        final List<String> spineHrefs = new ArrayList<>();
    }

    /**
     * Reads META-INF/container.xml to locate the OPF, then parses the OPF to recover
     * the spine order (as hrefs) and basic Dublin Core metadata. Returns null when
     * either file is missing or unparseable.
     */
    private static EpubOpfInfo readEpubOpf(
            org.apache.commons.compress.archivers.zip.ZipFile zf,
            Metadata metadata
    ) throws IOException {
        ZipArchiveEntry containerEntry = zf.getEntry("META-INF/container.xml");
        if (containerEntry == null || !zf.canReadEntryData(containerEntry)) {
            return null;
        }
        String opfPath;
        try (InputStream is = zf.getInputStream(containerEntry)) {
            opfPath = readOpfPathFromContainer(is);
        }
        if (opfPath == null) {
            return null;
        }
        ZipArchiveEntry opfEntry = zf.getEntry(opfPath);
        if (opfEntry == null || !zf.canReadEntryData(opfEntry)) {
            return null;
        }

        EpubOpfInfo info = new EpubOpfInfo();
        int slash = opfPath.lastIndexOf('/');
        if (slash > -1) {
            info.opfDir = opfPath.substring(0, slash + 1);
        }

        try (InputStream is = zf.getInputStream(opfEntry)) {
            parseOpfXml(is, info, metadata);
        } catch (IOException ioe) {
            throw ioe;
        } catch (Exception ex) {
            throw new IOException("Failed to parse OPF", ex);
        }
        return info;
    }

    /** Extracts the first rootfile/full-path from an EPUB container.xml. */
    private static String readOpfPathFromContainer(InputStream is) throws IOException {
        try {
            DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
            dbf.setNamespaceAware(true);
            DocumentBuilder db = dbf.newDocumentBuilder();
            Document doc = db.parse(is);
            NodeList roots = doc.getElementsByTagNameNS(
                    "urn:oasis:names:tc:opendocument:xmlns:container", "rootfile");
            if (roots.getLength() == 0) {
                roots = doc.getElementsByTagName("rootfile");
            }
            if (roots.getLength() == 0) {
                return null;
            }
            String path = ((Element) roots.item(0)).getAttribute("full-path");
            return path.isEmpty() ? null : path;
        } catch (Exception ex) {
            throw new IOException("Failed to parse container.xml", ex);
        }
    }

    /**
     * Parses an OPF document: records Dublin Core metadata (title/creator/language/...)
     * into the provided Metadata, and fills info.spineHrefs with item hrefs in spine order.
     */
    private static void parseOpfXml(InputStream is, EpubOpfInfo info, Metadata metadata) throws Exception {
        final String opfNs = "http://www.idpf.org/2007/opf";
        final String dcNs = "http://purl.org/dc/elements/1.1/";

        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setNamespaceAware(true);
        DocumentBuilder db = dbf.newDocumentBuilder();
        Document doc = db.parse(is);

        setIfAbsent(metadata, TikaCoreProperties.TITLE.getName(),
                firstElementText(doc, dcNs, "title"));
        setIfAbsent(metadata, TikaCoreProperties.CREATOR.getName(),
                firstElementText(doc, dcNs, "creator"));
        setIfAbsent(metadata, TikaCoreProperties.DESCRIPTION.getName(),
                firstElementText(doc, dcNs, "description"));
        setIfAbsent(metadata, TikaCoreProperties.PUBLISHER.getName(),
                firstElementText(doc, dcNs, "publisher"));
        setIfAbsent(metadata, TikaCoreProperties.LANGUAGE.getName(),
                firstElementText(doc, dcNs, "language"));
        setIfAbsent(metadata, TikaCoreProperties.IDENTIFIER.getName(),
                firstElementText(doc, dcNs, "identifier"));

        // Manifest: id -> href
        Map<String, String> idToHref = new HashMap<>();
        NodeList items = doc.getElementsByTagNameNS(opfNs, "item");
        if (items.getLength() == 0) {
            items = doc.getElementsByTagName("item");
        }
        for (int i = 0; i < items.getLength(); i++) {
            Element el = (Element) items.item(i);
            String id = el.getAttribute("id");
            String href = el.getAttribute("href");
            if (!id.isEmpty() && !href.isEmpty()) {
                idToHref.put(id, href);
            }
        }

        // Spine order
        NodeList itemRefs = doc.getElementsByTagNameNS(opfNs, "itemref");
        if (itemRefs.getLength() == 0) {
            itemRefs = doc.getElementsByTagName("itemref");
        }
        for (int i = 0; i < itemRefs.getLength(); i++) {
            Element el = (Element) itemRefs.item(i);
            String idref = el.getAttribute("idref");
            String href = idToHref.get(idref);
            if (href != null && !href.isEmpty()) {
                info.spineHrefs.add(href);
            }
        }
    }

    private static void setIfAbsent(Metadata metadata, String key, String value) {
        if (value != null && !value.isEmpty() && metadata.get(key) == null) {
            metadata.set(key, value);
        }
    }

    private static String firstElementText(Document doc, String ns, String local) {
        NodeList nodes = doc.getElementsByTagNameNS(ns, local);
        if (nodes.getLength() == 0) {
            nodes = doc.getElementsByTagName(local);
        }
        if (nodes.getLength() == 0) {
            return null;
        }
        String text = nodes.item(0).getTextContent();
        return text == null ? null : text.trim();
    }

    /**
     * This is the main entry point of the native image build. @CEntryPoint is used
     * because we do not want to build an executable with a main method. The gradle nativeImagePlugin
     * expects either a main method or @CEntryPoint
     * This uses the C Api isolate, which is can only work with primitive return types unlike the JNI invocation
     * interface.
     */
    @CEntryPoint(name = "c_parse_to_string")
    private static CCharPointer cParseToString(IsolateThread thread, @CConst CCharPointer cFilePath) {
        final String filePath = CTypeConversion.toJavaString(cFilePath);

        final Path path = Paths.get(filePath);
        try {
            final String content = tika.parseToString(path);
            try (CTypeConversion.CCharPointerHolder holder = CTypeConversion.toCString(content)) {
                return holder.get();
            }

        } catch (java.io.IOException | TikaException e) {
            throw new RuntimeException(e);
        }
    }

}
