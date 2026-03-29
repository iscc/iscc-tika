# iscc-tika

Fork of [yobix-ai/extractous](https://github.com/yobix-ai/extractous) revived under the ISCC organization.

## Project Overview

Fast text and metadata extraction from documents (PDF, Word, HTML, etc.) using Rust with Apache Tika compiled to native code via GraalVM.

## Architecture

- **iscc-tika-core/** — Rust core library (`iscc-tika` crate)
  - `src/` — Rust source (extractor, config, errors, tika bridge)
  - `tika-native/` — GraalVM-compiled Apache Tika (Gradle build)
  - `build.rs` — Downloads/builds tika-native libs during cargo build
- **bindings/iscc-tika-python/** — Python bindings via PyO3/maturin
  - `src/` — Rust PyO3 wrapper
  - `python/` — Pure Python module (`iscc_tika`)
  - `tests/` — Python tests
- **test_files/** — Sample documents for testing

## Build System

- Rust core: `cargo build` (requires tika-native libs)
- Python bindings: `maturin develop` (from `bindings/iscc-tika-python/`)
- Tika native: Gradle build in `iscc-tika-core/tika-native/`

## Key Technical Details

- Python package uses stable ABI (`abi3-py38`), minimum Python 3.8
- GraalVM shared libs are bundled into Python wheels
- RPATH set to `$ORIGIN` for lib discovery in wheels
- `skip-auditwheel=true` in maturin config (GraalVM lib compatibility)

## Testing

- Rust: `cargo test` in `iscc-tika-core/`
- Python: `pytest -s` in `bindings/iscc-tika-python/` (after `maturin develop -E test`)
