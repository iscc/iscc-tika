# Unreleased

### Breaking Changes

- Project renamed from `extractous` to `iscc-tika`. This is a fork of
    [yobix-ai/extractous](https://github.com/yobix-ai/extractous) maintained by the ISCC
    organization.
    - Rust crate: `extractous` -> `iscc-tika`
    - Python package: `extractous` -> `iscc-tika` (import as `iscc_tika`)
    - Java package: `ai.yobix` -> `io.iscc.tika`

### Bug Fixes

- Fix C-strings passed to GraalVM JNI invocation API. Use NUL-terminated C-string literals instead
    of Rust str pointers for JVM options, preventing potential memory issues when processing large
    numbers of files. Also fixes the missing hyphen in the `java.awt.headless` option.
    ([extractous#73](https://github.com/yobix-ai/extractous/pull/73))
- Fix `extract_unique_inline_images_only` default value from `false` to `true` to match Tika's own
    `PDFParserConfig` default. ([extractous#44](https://github.com/yobix-ai/extractous/issues/44))
- Add missing XMLMessages resource bundle to GraalVM reachability metadata. PDFs with XMP metadata
    caused `RuntimeException from PDFParser` because `org.apache.xerces.impl.msg.XMLMessages` was
    not included in the native image. Fixed for all platforms (Linux, macOS, Windows).
    ([extractous#56](https://github.com/yobix-ai/extractous/issues/56))
- Fix JNI AttachGuard lifetime in JReaderInputStream. The `AttachGuard` can now optionally be stored
    alongside `GlobalRef`s (via `stream-attachguard` feature flag) to ensure the JVM thread
    attachment outlives the references, preventing potential use-after-free issues.
    ([extractous#64](https://github.com/yobix-ai/extractous/pull/64),
    [jungnitz/extractous@b047ca8](https://github.com/jungnitz/extractous/commit/b047ca8))
- Fix incorrect default values in config docstrings: `include_headers_and_footers` (true -> false),
    `depth` (8 -> 4), `timeout_seconds` (120 -> 130). Docstrings now match the actual Tika defaults
    used in the `Default` implementations.
    ([ProSync/extractous@3c6506b](https://github.com/ProSync/extractous/commit/3c6506b))
- Prevent build panics when GraalVM header files are missing during artifact cleanup. Gracefully
    ignore missing `.h` files instead of unwrapping.
    ([ProSync/extractous@cac1e0f](https://github.com/ProSync/extractous/commit/cac1e0f))
- Handle EncryptedDocumentException gracefully instead of failing extraction. Documents with
    encrypted items (e.g. DRM-protected fonts in EPUBs) now return extracted text with a warning in
    metadata (`X-TIKA:warning`) instead of raising a `ParseError`.

### Development

- Add quality gates via prek (drop-in pre-commit replacement) with dual-stage hooks: fast auto-fix
    on pre-commit (file hygiene, cargo-fmt, ruff, taplo, yamlfix, mdformat) and thorough checks on
    pre-push (cargo-clippy, cargo-test, security scan, complexity check, pytest).
- Add mise task runner with `check`, `lint`, `format`, `test`, `version:check`, and `pr:main` tasks.
- Add ruff configuration with complexity threshold (max 15) and per-file ignores for tests.
- Add clippy cognitive complexity threshold (max 15, Radon grade C).
- Configure rustfmt to enforce Unix line endings (`newline_style = "Unix"`) for cross-platform
    consistency.
- Add `pytest-timeout` to Python test dependencies with a default 120-second timeout.

### DevContainer

- Install mise (task runner) in devcontainer image.
- Add `setup-dev.sh` script to install dev tools (prek, ruff, taplo, yamlfix, mdformat) and git
    hooks automatically on container creation.
- Add copyright information to LICENSE for original author and fork maintainer.
- Persist build caches across devcontainer rebuilds by removing `${devcontainerId}` from Docker
    volume names.
- Add dedicated Docker volume for Rust `target/` directory to avoid slow Windows bind mount I/O for
    build artifacts.
- Configure container resource limits (4 CPUs, 16 GB RAM) for faster compilation.
- Add `mold` linker and `sccache` for faster Rust builds inside the devcontainer.
- Add `.cargo/config.toml` with `mold` linker configuration for Linux targets.

### Enhancements

- Enable Python 3.14 support by bumping `requires-python` upper bound to `<3.15`.
    ([extractous#76](https://github.com/yobix-ai/extractous/pull/76),
    [extractous#70](https://github.com/yobix-ai/extractous/issues/70))
- Replace all Rust build dependencies (`reqwest`, `zip`, `flate2`, `tar`, `walkdir`, `fs_extra`)
    with a Python stdlib script (`setup_tika_native.py`). Reduces build-time compilation overhead
    significantly. Python 3.8+ is now required at build time (already present for the bindings).
- Remove `native-tls` and `rustls` feature flags (superseded by the Python-based build script which
    uses `urllib.request` for GraalVM downloads).

# [](https://github.com/yobix-ai/extractous/compare/v0.1.5...v) (2024-10-30)

### Bug Fixes

- add criterion benchmarks
    ([5858356](https://github.com/yobix-ai/extractous/commit/585835623bb7c098e4359636d8d028af4835d699))
- fixed issue 16 and added test case
    ([03062be](https://github.com/yobix-ai/extractous/commit/03062beca1eceede16878707dc2647b71848b65e))
- minor fix to build script
    ([8ac14b8](https://github.com/yobix-ai/extractous/commit/8ac14b8d36c8a8d733c08a123686d02c52bcf5bb))

## [0.1.5](https://github.com/yobix-ai/extractous/compare/v0.1.4...v0.1.5) (2024-10-29)

### Bug Fixes

- add python extension dir to the windows PATH to find graalvm libs
    ([8cd1240](https://github.com/yobix-ai/extractous/commit/8cd1240cb0dfca7e67f4254d34947bb9c7fa5c25))
- don't copy libs to same dir
    ([e5dad2f](https://github.com/yobix-ai/extractous/commit/e5dad2f7434b8cae58b6aa61c0c66165473aa35f))
- don't create graalvm archive if download fails
    ([2c84a50](https://github.com/yobix-ai/extractous/commit/2c84a5005bbea993d57e187a1f7f7f73ca8c3f87))
- don't include static lib on windows + bump release version
    ([02ed47f](https://github.com/yobix-ai/extractous/commit/02ed47fd79572acc671309188adb8dcb2995592a))

### Features

- implemented windows support + updated readme with ocr
    ([17b5663](https://github.com/yobix-ai/extractous/commit/17b5663b4f852396646ec43c03f0fb888825d750))

## [0.1.4](https://github.com/yobix-ai/extractous/compare/v0.1.3...v0.1.4) (2024-09-18)

### Bug Fixes

- added missing python bindings for config module
    ([fc4d90a](https://github.com/yobix-ai/extractous/commit/fc4d90adf29b277b32d21aef368e1919eeed2544))
- remove unenessary liftimes
    ([b321df6](https://github.com/yobix-ai/extractous/commit/b321df6e743273ed02b229cf152b9554f610914e))
- tolerate invalid utf8 chars when converting to string
    ([24a45e7](https://github.com/yobix-ai/extractous/commit/24a45e79740ad69aca3bdddf182aa56b64640965))

### Features

- add buffer to JReaderInputStream and reuse it to not call new_byte_array on every read
    ([881d919](https://github.com/yobix-ai/extractous/commit/881d9190f7047163a497d2b2e578eca1f7b890ef))
- refactor examples
    ([8a7f9a3](https://github.com/yobix-ai/extractous/commit/8a7f9a3ba7b5db4e07a07efbe516dfbdcd52f79d))
- replace PyBytes with PyBytesArray in the StreamReader
    ([20c2944](https://github.com/yobix-ai/extractous/commit/20c294465b3ac158c75f6b389fc2d35fcbe137a3))
- reuse buffer in python StreamReader wrapper
    ([8ccaf04](https://github.com/yobix-ai/extractous/commit/8ccaf04d7fce81da9dec2694fc7b7942be55cf32))

## [0.1.3](https://github.com/yobix-ai/extractous/compare/v0.1.1...v0.1.3) (2024-09-11)

## [0.1.1](https://github.com/yobix-ai/extractous/compare/a86462cc49b77f9e17b8faade80edaf679edf225...v0.1.1) (2024-09-11)

### Bug Fixes

- add missing jni entry for parseToString method
    ([21cf299](https://github.com/yobix-ai/extractous/commit/21cf299cc4d3c952d7ebaa793b9a5c4e16069d64))
- add more reahability data
    ([fd2cb3a](https://github.com/yobix-ai/extractous/commit/fd2cb3ad0a1af19814350d61b533117273f65a8a))
- move lib artifacts to deps folder
    ([b150ca9](https://github.com/yobix-ai/extractous/commit/b150ca9f316352b488eff06904555c0d0620c6ce))
- return StreamReader when extracting
    ([b20209a](https://github.com/yobix-ai/extractous/commit/b20209a9e49c19565fabe6ead799519d5582e010))
- update reachability data
    ([77a0aae](https://github.com/yobix-ai/extractous/commit/77a0aaef42beb1fe61dd2b93aad9a1c24a1b74c8))
- update tika-native
    ([e009af9](https://github.com/yobix-ai/extractous/commit/e009af9a942e9e861ae985d6629356c89dd28534))

### Features

- adapted the python binding to work with the new extractor api
    ([0f78452](https://github.com/yobix-ai/extractous/commit/0f78452ef0c107c34ba4f13580480622b0659d86))
- add jni helper functions to print to stderr in case of java exception is thrown
    ([2b7d641](https://github.com/yobix-ai/extractous/commit/2b7d641e137818681bca63c0f3c156e4c76dbd09))
- add StreamReader struct and make JReaderInputStream takes a GlobalRef
    ([4bfa895](https://github.com/yobix-ai/extractous/commit/4bfa895b7f97c4a5467e0ae3fd6c252f272e3b03))
- add tika-native source files
    ([78344e8](https://github.com/yobix-ai/extractous/commit/78344e88d7e9b14478ea83196659f9ab0c381a12))
- better error reporting
    ([1e96cf5](https://github.com/yobix-ai/extractous/commit/1e96cf525ec56aa362904fbb71c914684027d5a1))
- implemented extracting to a streamed reader
    ([b6533be](https://github.com/yobix-ai/extractous/commit/b6533be5507f3513e17d4677b477e6e6a6cc6bc6))
- initial integration of tika-native into rust
    ([579e6cd](https://github.com/yobix-ai/extractous/commit/579e6cd73d53088feca5f41be80dab4026d485f8))
- initial project sturcture
    ([a86462c](https://github.com/yobix-ai/extractous/commit/a86462cc49b77f9e17b8faade80edaf679edf225))
- introduced extractor builder pattern
    ([6d091f8](https://github.com/yobix-ai/extractous/commit/6d091f84c70a2f4338921e6c801bc0b4a8942603))
- parseFile with all config wrapper objects
    ([a7c39c4](https://github.com/yobix-ai/extractous/commit/a7c39c43d37cb92e63b1714264898c733b0ea6f5))
- renamed python binding to extractous
    ([8041fd4](https://github.com/yobix-ai/extractous/commit/8041fd4319b87864b52f53081fcb3fc0b02563fb))
