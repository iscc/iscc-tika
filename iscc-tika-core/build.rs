use std::env;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    // Exit early when building docs
    if env::var("DOCS_RS").is_ok() {
        return;
    }

    let root_dir = env::var("CARGO_MANIFEST_DIR").map(PathBuf::from).unwrap();
    let out_dir = env::var("OUT_DIR").map(PathBuf::from).unwrap();
    let libs_out_dir = out_dir.join("libs");

    // Target platform (set by Cargo for build scripts)
    let target_os = env::var("CARGO_CFG_TARGET_OS").unwrap();
    let target_arch = env::var("CARGO_CFG_TARGET_ARCH").unwrap();

    // Python binding directory (only passed when it exists)
    let python_bind_dir = root_dir.join("../bindings/iscc-tika-python/python/iscc_tika");

    let python = find_python();
    let script = root_dir.join("setup_tika_native.py");

    let mut cmd = Command::new(&python);
    cmd.arg(&script)
        .arg("--manifest-dir")
        .arg(&root_dir)
        .arg("--out-dir")
        .arg(&out_dir)
        .arg("--target-os")
        .arg(&target_os)
        .arg("--target-arch")
        .arg(&target_arch);

    if python_bind_dir.is_dir() {
        cmd.arg("--python-bind-dir").arg(&python_bind_dir);
    }

    let status = cmd.status().unwrap_or_else(|e| {
        panic!(
            "Failed to run Python ({python:?}) for build setup: {e}\n\
             Please ensure Python 3.8+ is installed and available as 'python3' or 'python'.\n\
             You can also set the PYTHON environment variable to the interpreter path."
        );
    });

    if !status.success() {
        panic!("setup_tika_native.py failed (exit code: {status})");
    }

    // Tell cargo to look for shared libraries in the specified directory
    println!("cargo:rustc-link-search={}", libs_out_dir.display());

    // Tell cargo to link the tika_native shared library
    let lib_name = if target_os == "windows" {
        "libtika_native"
    } else {
        "tika_native"
    };
    println!("cargo:rustc-link-lib=dylib={lib_name}");
}

/// Find a Python 3 interpreter.
///
/// Priority: PYTHON env var > platform-appropriate default > fallback.
fn find_python() -> String {
    if let Ok(python) = env::var("PYTHON") {
        return python;
    }

    // On Windows `python` is the standard name; on Unix `python3` is preferred
    let candidates: &[&str] = if cfg!(target_os = "windows") {
        &["python", "python3"]
    } else {
        &["python3", "python"]
    };

    for candidate in candidates {
        if Command::new(candidate)
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
        {
            return candidate.to_string();
        }
    }

    panic!(
        "Python 3.8+ not found. Please install Python and ensure 'python3' or 'python' \
         is on your PATH, or set the PYTHON environment variable."
    );
}
