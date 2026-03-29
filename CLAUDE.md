# iscc-tika

Fork of [yobix-ai/extractous](https://github.com/yobix-ai/extractous) being revived and renamed to `iscc-tika`.

## Project Overview

Fast text and metadata extraction from documents (PDF, Word, HTML, etc.) using Rust with Apache Tika compiled to native code via GraalVM.

## Architecture

- **extractous-core/** — Rust core library (`extractous` crate)
  - `src/` — Rust source (extractor, config, errors, tika bridge)
  - `tika-native/` — GraalVM-compiled Apache Tika (Gradle build)
  - `build.rs` — Downloads/builds tika-native libs during cargo build
- **bindings/extractous-python/** — Python bindings via PyO3/maturin
  - `src/` — Rust PyO3 wrapper
  - `python/` — Pure Python module (`extractous`)
  - `tests/` — Python tests
- **test_files/** — Sample documents for testing

## Build System

- Rust core: `cargo build` (requires tika-native libs)
- Python bindings: `maturin develop` (from `bindings/extractous-python/`)
- Tika native: Gradle build in `extractous-core/tika-native/`

## Key Technical Details

- Python package uses stable ABI (`abi3-py38`), minimum Python 3.8
- GraalVM shared libs are bundled into Python wheels
- RPATH set to `$ORIGIN` for lib discovery in wheels
- `skip-auditwheel=true` in maturin config (GraalVM lib compatibility)

## Testing

- Rust: `cargo test` in `extractous-core/`
- Python: `pytest -s` in `bindings/extractous-python/` (after `maturin develop -E test`)

## Renaming Status

The project is being renamed from `extractous` to `iscc-tika`. This involves updating:
- Package names (crate, PyPI)
- Module names and imports
- Repository URLs and documentation links
- Branding and references
