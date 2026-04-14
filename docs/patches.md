# Local patches and workarounds

This file tracks local patches applied on top of Apache Tika or other upstream dependencies. For
each entry, record: the upstream bug, the local workaround, where it lives in the code, and whether
an upstream fix has been filed.

## EPUB — lenient fallback for `TIKA-198` and `TIKA-237` from EpubParser

- **Applied:** 2026-04-13 (TIKA-198), extended 2026-04-13 (TIKA-237)
- **Affects:** Apache Tika 3.3.0 (confirmed still present on `master`)
- **Scope:** `TikaNativeMain.parseFileToString` and `TikaNativeMain.parseBytesToString`
- **Upstream:** not yet filed — no matching ticket found on Apache Tika Jira or GitHub

### Symptom

`Extractor.extract_file_to_string` on certain EPUBs raises:

```
ParseError: Parse error occurred : TIKA-198: Illegal IOException from
org.apache.tika.parser.epub.EpubParser@<id>
```

Reproducer in-tree: `cauldron/error-files/tika-198-ioexception_9788412435931.epub`

### Root cause

`org.apache.tika.parser.epub.EpubParser.bufferedParseZipFile` performs a strict content-item
existence check. For each manifest item it concatenates the OPF's parent directory with the item's
`href` and calls `ZipFile.getEntry(...)` on the *literal* resulting string. Commons-compress
`ZipFile.getEntry` does not normalize `..` segments.

The failing EPUB's `OEBPS/content.opf` manifest contains:

```xml
<item id="id5" href="../toc.xhtml" media-type="application/xhtml+xml" />
```

`toc.xhtml` really does exist at the archive root (alongside `META-INF/` and `OEBPS/`), but Tika
looks up the literal `"OEBPS/../toc.xhtml"` — which is not a valid zip entry name — and gets `null`.
The counter `found` ends up `contentItems.size() - 1`, tripping the strict check and throwing
`EpubParser$EpubZipException` (a private `IOException` subclass) from around line 292 of
`EpubParser.java`.

`CompositeParser.parse` then catches the `IOException`, sees it is not caused by the
`TaggedInputStream` wrapping the main input, and re-wraps it as
`TikaException("TIKA-198: Illegal IOException from " + parser, e)`.

Note that `bufferedParse` only has a salvage fallback path (`trySalvage` → `streamingParse`) for the
case where `ZipFile.builder().setFile(...).get()` itself throws. A strict-mode mismatch on an
*openable* zip propagates straight up with no recovery — so every EPUB that hits this path dies.

### Workaround

When `parseFileToString` / `parseBytesToString` catch a `TikaException`, the
`isEpubLenientCandidate(TikaException, Metadata)` predicate decides whether to retry via
`lenientEpubParseToString(Path, ...)`. Both branches first require the file to be an EPUB-family
container — either by naming `EpubParser` in the wrapped message or by the detected content type
being `application/epub+zip` or `application/x-ibooks+zip` (both media types are registered by
`EpubParser`). Then:

- **TIKA-198** retries unconditionally — the strict content-item check is the only code path that
    raises it.
- **TIKA-237** retries only when `rootMessage(e)` contains `"zip bomb"`, i.e. when the root SAX
    error is Tika's `SecureContentHandler` zip-bomb defense misfiring on legitimate deep XHTML
    nesting. Other SAX errors (malformed XHTML, broken entities, etc.) surface as hard failures so
    they are not silently converted into lenient successes.

The fallback:

1. Opens the file with `commons-compress` `ZipFile` directly.
2. Reads `META-INF/container.xml` to locate the OPF.
3. Parses the OPF (DOM) to recover Dublin Core metadata and the ordered list of spine hrefs.
4. For each spine href, resolves the entry path via `Paths.get(opfDir + href).normalize()` —
    collapsing `..` segments — and falls back to `zipFile.getEntry(...)`.
5. Runs `AutoDetectParser` on the entry, wrapping the outer handler with `EmbeddedContentHandler` so
    nested `startDocument`/`endDocument` events do not close the outer document scope.
6. Individual entry failures are recorded as `X-TIKA:warning` metadata entries but do not abort the
    overall parse.

A `X-TIKA:warning` metadata entry is added on every fallback invocation so callers can tell the
lenient path was used.

## EPUB — lenient fallback for `TIKA-237: Illegal SAXException` (deep XHTML nesting)

### Symptom

`Extractor.extract_file_to_string` on certain EPUBs raises:

```
ParseError: Parse error occurred : TIKA-237: Illegal SAXException from
org.apache.tika.parser.DefaultParser@<id>
```

Reproducer in-tree: `cauldron/error-files/tika-237-saxexception_9791220847322.epub`

### Root cause

The actual trigger is Tika's TIKA-216 zip-bomb prevention, not a JDK XML parser limit.
`AutoDetectParser.parse` wraps the caller's handler in a `SecureContentHandler` (around line 192 of
`AutoDetectParser.java`) that counts `startElement`/`endElement` pairs and throws a `SAXException`
with message `"Suspected zip bomb: <N> levels of XML element nesting"` once the depth exceeds its
default limit (100 levels).

The reproducer's `OEBPS/chapter.3.xhtml` stacks 258 levels of nested `<div>` (one per line of
verse). When `EpubParser.bufferedParseZipFile` feeds that entry to `EpubContentParser.parse` →
`XMLReaderUtils.parseSAX`, the SAX events flow through the handler chain
`EmbeddedContentHandler → EpubNormalizingHandler → BodyContentHandler → XHTMLContentHandler → SecureContentHandler → user handler`.
The `SecureContentHandler` trips at depth 101, throws the "zip bomb" SAX error,
`bufferedParseZipFile` collects it at the entry-loop `catch (SAXException)`, and re-throws at the
end of the loop. `CompositeParser.parse` then wraps it as `TIKA-237: Illegal SAXException`.

The wrapped message surfaces the outer composite parser (`org.apache.tika.parser.DefaultParser@…`),
not `EpubParser`, so message matching on `"EpubParser"` is not sufficient to detect the case. The
detection predicate also accepts the file when `Metadata.CONTENT_TYPE` is one of the EPUB-family
media types registered by `EpubParser` (`application/epub+zip` or `application/x-ibooks+zip`) — the
content type is set by `AutoDetectParser.detector.detect` before delegation, so it is reliably
populated by the time the exception is caught.

Because TIKA-237 is CompositeParser's generic wrapper for *any* `SAXException` from `EpubParser`,
the predicate additionally requires `rootMessage(e)` to contain `"zip bomb"` before retrying. That
keeps unrelated SAX failures (malformed XHTML, broken entities, stray tags) surfacing as hard errors
instead of being silently salvaged by the lenient path.

The blast radius is intentionally scoped to EPUB content: TIKA-216 is meant to prevent DoS via
maliciously nested XML, and legitimate content like verse poetry can trip it by accident. Relaxing
globally would defeat the zip-bomb defense for every parser; per-entry re-parsing contains the risk.

### Workaround

Shared with the TIKA-198 path: `lenientEpubParseToString` runs `AutoDetectParser` per spine entry,
which detects XHTML as `application/xhtml+xml` and routes it through the TagSoup-backed HTML parser.
TagSoup handles deep element nesting without hitting the SAX depth limit, so the failing chapter is
extracted successfully. Other entries parse on the same lenient path and individual failures are
recorded as warnings rather than aborting the overall parse.

### What is NOT covered

- `parseFile` / `parseUrl` (reader-based streaming API). These go through `ParsingReader`, which
    runs the parse on a background thread and only surfaces errors when the caller reads from the
    reader. A similar fallback would need either a probe-first strategy or a retry mechanism that
    re-opens the file — deferred for now. Callers who hit this on the reader API should use
    `extract_file_to_string` as a workaround.

### Removing this workaround

Once Apache Tika ships fixes for both cases, delete:

- `isEpubLenientCandidate`, `rootMessage`, `dumpToTempFile`, `lenientEpubParseToString`,
    `resolveEpubEntryPath`, `EpubOpfInfo`, `readEpubOpf`, `readOpfPathFromContainer`, `parseOpfXml`,
    `setIfAbsent`, `firstElementText` in `TikaNativeMain.java`.
- The `catch (TikaException e)` branches inside `parseFileToString` / `parseBytesToString` that call
    into the fallback.
- The `org.apache.commons.compress.archivers.zip.ZipArchiveEntry` import and any
    `javax.xml.parsers.*` / `org.w3c.dom.*` imports that are no longer needed.

### Upstream action items

- File an Apache Tika Jira ticket for `TIKA-198` with the reproducer EPUB. Suggested fix:

    ```java
    // EpubParser.bufferedParseZipFile, around line 283
    String resolved = Paths.get(relativePath + hRefMediaPair.href)
                           .normalize()
                           .toString()
                           .replace('\\', '/');
    zae = zipFile.getEntry(resolved);
    ```

    plus — as defense in depth — letting `bufferedParse` catch `EpubZipException` and fall through to
    `streamingParse`, matching the semantics of the existing `trySalvage` path.

- File an Apache Tika Jira ticket for `TIKA-237` with the deep-nesting reproducer EPUB. Two possible
    fixes upstream:

    1. Allow a larger maximum depth in `SecureContentHandler` when the parse is for an EPUB content
        item (the zip bomb heuristic still matters, but 100 levels is too low for typeset verse).
    2. Let `EpubParser.bufferedParseZipFile`'s per-entry `catch (SAXException)` treat zip-bomb SAX
        errors as per-entry warnings rather than re-throwing at the end of the loop, so one failing
        XHTML entry does not abort the whole EPUB.
