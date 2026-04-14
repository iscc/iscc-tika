## Changelog

## Unreleased

- Added metadata-only extraction API: `extract_file_metadata`, `extract_bytes_metadata`, and
    `extract_url_metadata` on `Extractor` and the Python bindings. Skipping content extraction is
    typically 2–5× faster on text-heavy PDFs because PDFBox glyph rendering is bypassed.
- Upgraded to Apache Tika 3.3.0, GraalVM CE 25.0.2, and Gradle 9.2.0 (from Tika 2.9.2 EOL). Includes
    the `javax` → `jakarta` migration for mail dependencies, `BodyContentHandler` API fixes, and
    GraalVM 25 build flags (`RemoveUnusedSymbols`, `ReportExceptionStackTraces`).
- Added lenient EPUB fallback for `TIKA-198: Illegal IOException from EpubParser`. Tika 3.3.0's
    `EpubParser.bufferedParseZipFile` strict check does not normalize `..` segments, so EPUBs whose
    OPF references entries via `href="../foo.xhtml"` throw `EpubZipException`.
    `extract_file_to_string` / `extract_bytes_to_string` now fall back to parsing spine entries
    directly via `commons-compress` + `AutoDetectParser`, collapsing `..` via `Path.normalize`, and
    record a warning in `X-TIKA:warning`. See `docs/patches.md` for the full root-cause analysis.
    The reader-based API (`extract_file` / `extract_bytes`) is not yet covered.
- Extended the lenient EPUB fallback to cover `TIKA-237: Illegal SAXException`, caused by Tika's
    `SecureContentHandler` zip-bomb detector (default max XML element nesting 100). EPUBs with
    deeply nested `<div>` content now retry spine parsing through a fresh `AutoDetectParser` when
    the container is EPUB-family and the root cause mentions `"zip bomb"`.
- Marked OCR tests as `#[ignore]` so local `cargo test` runs stay fast; run with `--ignored` (or in
    CI) to execute them.
- Fixed devcontainer gitconfig setup so the host identity survives rebuilds.
- Fixed devcontainer `NODE_OPTIONS` handling for Zed.
- Updated README to reference ISCC Foundation and iscc.io.

## 0.4.0 - 2026-03-29

- Forked from [yobix-ai/extractous](https://github.com/yobix-ai/extractous) and revived under the
    ISCC organization. Upstream is no longer maintained.
- Renamed Rust crate from `extractous` to `iscc-tika`.
- Renamed Python package from `extractous` to `iscc-tika` (import as `iscc_tika`).
- Renamed Java package from `ai.yobix` to `io.iscc.tika`.
- Enabled Python 3.14 support by bumping `requires-python` upper bound to `<3.15`
    ([extractous#76](https://github.com/yobix-ai/extractous/pull/76),
    [extractous#70](https://github.com/yobix-ai/extractous/issues/70)).
- Replaced all Rust build dependencies (`reqwest`, `zip`, `flate2`, `tar`, `walkdir`, `fs_extra`)
    with a Python stdlib script (`setup_tika_native.py`) to reduce build-time compilation overhead.
    Python 3.8+ is now required at build time.
- Removed `native-tls` and `rustls` feature flags, superseded by the Python-based build script which
    uses `urllib.request` for GraalVM downloads.
- Added `cargo:rerun-if-changed` directives to `build.rs` so the build script only re-runs when
    `tika-native/` source files actually change, skipping the costly GraalVM/Gradle check on
    consecutive cargo invocations.
- Fixed C-strings passed to GraalVM JNI invocation API. Uses NUL-terminated C-string literals
    instead of Rust `str` pointers for JVM options, preventing memory issues when processing large
    numbers of files. Also fixes the missing hyphen in the `java.awt.headless` option
    ([extractous#73](https://github.com/yobix-ai/extractous/pull/73)).
- Fixed `extract_unique_inline_images_only` default from `false` to `true` to match Tika's own
    `PDFParserConfig` default ([extractous#44](https://github.com/yobix-ai/extractous/issues/44)).
- Fixed missing XMLMessages resource bundle in GraalVM reachability metadata. PDFs with XMP metadata
    no longer trigger `RuntimeException from PDFParser` on any platform (Linux, macOS, Windows)
    ([extractous#56](https://github.com/yobix-ai/extractous/issues/56)).
- Fixed JNI AttachGuard lifetime in `JReaderInputStream`. The guard can now optionally be stored
    alongside `GlobalRef`s via the `stream-attachguard` feature flag, ensuring the JVM thread
    attachment outlives the references and preventing use-after-free issues
    ([extractous#64](https://github.com/yobix-ai/extractous/pull/64),
    [jungnitz/extractous@b047ca8](https://github.com/jungnitz/extractous/commit/b047ca8)).
- Fixed incorrect default values in config docstrings: `include_headers_and_footers` (true → false),
    `depth` (8 → 4), `timeout_seconds` (120 → 130). Docstrings now match the actual Tika defaults
    used in the `Default` implementations
    ([ProSync/extractous@3c6506b](https://github.com/ProSync/extractous/commit/3c6506b)).
- Fixed build panics when GraalVM header files are missing during artifact cleanup. Gracefully
    ignores missing `.h` files instead of unwrapping
    ([ProSync/extractous@cac1e0f](https://github.com/ProSync/extractous/commit/cac1e0f)).
- Fixed PyPI publishing: dropped the macOS x86_64 wheel and TestPyPI step, disabled attestations,
    and restricted the `maturin include` glob to `python/iscc_tika/` so duplicate native libs from
    `target/` no longer triple the wheel size (~135 MB → ~42 MB).
- Handled `EncryptedDocumentException` gracefully instead of failing extraction. Documents with
    encrypted items (e.g. DRM-protected fonts in EPUBs) now return extracted text with a warning in
    `X-TIKA:warning` instead of raising a `ParseError`.
- Added quality gates via prek (drop-in pre-commit replacement) with dual-stage hooks: fast auto-fix
    on pre-commit (file hygiene, cargo-fmt, ruff, taplo, yamlfix, mdformat) and thorough checks on
    pre-push (cargo-clippy, cargo-test, security scan, complexity check, pytest).
- Added mise task runner with `check`, `lint`, `format`, `test`, `version:check`, and `pr:main`
    tasks.
- Added ruff configuration with mccabe complexity threshold 15 and per-file ignores for tests.
- Added clippy cognitive complexity threshold 15 (Radon grade C).
- Configured rustfmt to enforce Unix line endings (`newline_style = "Unix"`) for cross-platform
    consistency.
- Added `pytest-timeout` to Python test dependencies with a default 120-second timeout.
- Added `setup-dev.sh` to install dev tools (prek, ruff, taplo, yamlfix, mdformat) and git hooks
    automatically on devcontainer creation, and installed mise in the devcontainer image.
- Added Tesseract OCR and language packs to the devcontainer.
- Added copyright information to LICENSE for the original author and fork maintainer.
- Persisted build caches across devcontainer rebuilds by removing `${devcontainerId}` from Docker
    volume names, and added a dedicated Docker volume for the Rust `target/` directory to avoid slow
    Windows bind mount I/O for build artifacts.
- Configured devcontainer resource limits (4 CPUs, 16 GB RAM) and added the `mold` linker with a
    `.cargo/config.toml` for faster Rust linking on Linux targets.

## Pre-0.4.0

Historical releases (0.1.x) were published under
[yobix-ai/extractous](https://github.com/yobix-ai/extractous) before the fork. See the upstream
[CHANGELOG](https://github.com/yobix-ai/extractous/blob/main/CHANGELOG.md) for details.
