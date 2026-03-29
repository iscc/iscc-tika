# iscc-tika

Fork of [yobix-ai/extractous](https://github.com/yobix-ai/extractous) revived under the ISCC
organization.

## Project Overview

Fast text and metadata extraction from documents (PDF, Word, HTML, etc.) using Rust with Apache Tika
compiled to native code via GraalVM.

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

## Quality Gates

Quality gates are managed via prek (drop-in pre-commit replacement) with dual-stage hooks:

- **Pre-commit** (fast, auto-fix): file hygiene, mdformat, cargo-fmt, ruff, taplo, yamlfix
- **Pre-push** (thorough): cargo-clippy (`-D warnings`), cargo-test, security scan (ruff S),
    complexity check (ruff C901), pytest

Install hooks: `prek install && prek install --hook-type pre-push`

### Mise Tasks

Run tasks with `mise run <task>`:

- `check` — Run all pre-commit hooks on all files
- `lint` — Run format checks, clippy, and ruff
- `format` — Run pre-commit auto-fix hooks
- `test` — Run all tests (cargo test + pytest)
- `version:check` — Check that core and Python package versions match
- `pr:main` — Create a PR from develop to main

### Dev Tool Setup (one-time)

```bash
uv tool install prek ruff taplo yamlfix
uv tool install mdformat --with 'mdformat-mkdocs[recommended]'
prek install && prek install --hook-type pre-push
```

In the devcontainer, `.devcontainer/setup-dev.sh` handles this automatically.

### Linting Configuration

- Rust: `clippy.toml` — cognitive complexity threshold 15
- Rust: `rustfmt.toml` — Unix line endings enforced (`newline_style = "Unix"`)
- Python: `ruff.toml` — mccabe complexity 15, `S101` ignored in tests, `F403`/`F405` ignored in
    `__init__.py`
- No Cargo workspace at root — cargo commands use `--manifest-path` for each crate

## Testing

- Rust: `cargo test --manifest-path iscc-tika-core/Cargo.toml`
- Python: `pytest -s` in `bindings/iscc-tika-python/` (after `maturin develop -E test`)
- Combined: `mise run test`
