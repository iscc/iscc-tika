# Local patches and workarounds

This file tracks local patches applied on top of Apache Tika or other upstream
dependencies. For each entry, record: the upstream bug, the local workaround,
where it lives in the code, and whether an upstream fix has been filed.

## EPUB — lenient fallback for `TIKA-198: Illegal IOException from EpubParser`

**Applied:** 2026-04-13
**Affects:** Apache Tika 3.3.0 (confirmed still present on `master`)
**Scope:** `TikaNativeMain.parseFileToString` and `TikaNativeMain.parseBytesToString`
**Upstream:** not yet filed — no matching ticket found on Apache Tika Jira or GitHub

### Symptom

`Extractor.extract_file_to_string` on certain EPUBs raises:

```
ParseError: Parse error occurred : TIKA-198: Illegal IOException from
org.apache.tika.parser.epub.EpubParser@<id>
```

Reproducer in-tree:
`cauldron/error-files/tika-198-ioexception_9788412435931.epub`

### Root cause

`org.apache.tika.parser.epub.EpubParser.bufferedParseZipFile` performs a strict
content-item existence check. For each manifest item it concatenates the OPF's
parent directory with the item's `href` and calls `ZipFile.getEntry(...)` on
the *literal* resulting string. Commons-compress `ZipFile.getEntry` does not
normalize `..` segments.

The failing EPUB's `OEBPS/content.opf` manifest contains:

```xml
<item id="id5" href="../toc.xhtml" media-type="application/xhtml+xml"/>
```

`toc.xhtml` really does exist at the archive root (alongside `META-INF/` and
`OEBPS/`), but Tika looks up the literal `"OEBPS/../toc.xhtml"` — which is not
a valid zip entry name — and gets `null`. The counter `found` ends up
`contentItems.size() - 1`, tripping the strict check and throwing
`EpubParser$EpubZipException` (a private `IOException` subclass) from around
line 292 of `EpubParser.java`.

`CompositeParser.parse` then catches the `IOException`, sees it is not caused
by the `TaggedInputStream` wrapping the main input, and re-wraps it as
`TikaException("TIKA-198: Illegal IOException from " + parser, e)`.

Note that `bufferedParse` only has a salvage fallback path (`trySalvage` →
`streamingParse`) for the case where `ZipFile.builder().setFile(...).get()`
itself throws. A strict-mode mismatch on an *openable* zip propagates straight
up with no recovery — so every EPUB that hits this path dies.

### Workaround

When `parseFileToString` / `parseBytesToString` catch a `TikaException` whose
message matches `TIKA-198` + `EpubParser`, they retry via
`lenientEpubParseToString(Path, ...)`. The fallback:

1. Opens the file with `commons-compress` `ZipFile` directly.
2. Reads `META-INF/container.xml` to locate the OPF.
3. Parses the OPF (DOM) to recover Dublin Core metadata and the ordered list
   of spine hrefs.
4. For each spine href, resolves the entry path via
   `Paths.get(opfDir + href).normalize()` — collapsing `..` segments — and
   falls back to `zipFile.getEntry(...)`.
5. Runs `AutoDetectParser` on the entry, wrapping the outer handler with
   `EmbeddedContentHandler` so nested `startDocument`/`endDocument` events do
   not close the outer document scope.
6. Individual entry failures are recorded as `X-TIKA:warning` metadata
   entries but do not abort the overall parse.

A `X-TIKA:warning` metadata entry is added on every fallback invocation so
callers can tell the lenient path was used.

### What is NOT covered

- `parseFile` / `parseUrl` (reader-based streaming API). These go through
  `ParsingReader`, which runs the parse on a background thread and only
  surfaces errors when the caller reads from the reader. A similar fallback
  would need either a probe-first strategy or a retry mechanism that
  re-opens the file — deferred for now. Callers who hit this on the reader
  API should use `extract_file_to_string` as a workaround.

### Removing this workaround

Once Apache Tika ships a fix (either normalizing the concatenated path in
`bufferedParseZipFile` or catching `EpubZipException` in `bufferedParse` to
fall through to `streamingParse`), delete:

- `isEpubTika198`, `rootMessage`, `dumpToTempFile`, `lenientEpubParseToString`,
  `resolveEpubEntryPath`, `EpubOpfInfo`, `readEpubOpf`,
  `readOpfPathFromContainer`, `parseOpfXml`, `setIfAbsent`,
  `firstElementText` in `TikaNativeMain.java`.
- The `catch (TikaException e)` branches inside `parseFileToString` /
  `parseBytesToString` that call into the fallback.
- The `org.apache.commons.compress.archivers.zip.ZipArchiveEntry` import and
  any `javax.xml.parsers.*` / `org.w3c.dom.*` imports that are no longer
  needed.

### Upstream action items

- File an Apache Tika Jira ticket with the reproducer EPUB. Suggested fix:

  ```java
  // EpubParser.bufferedParseZipFile, around line 283
  String resolved = Paths.get(relativePath + hRefMediaPair.href)
                         .normalize()
                         .toString()
                         .replace('\\', '/');
  zae = zipFile.getEntry(resolved);
  ```

  plus — as defense in depth — letting `bufferedParse` catch
  `EpubZipException` and fall through to `streamingParse`, matching the
  semantics of the existing `trySalvage` path.
