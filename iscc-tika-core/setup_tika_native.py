#!/usr/bin/env python3
"""Setup tika-native libraries for iscc-tika Rust build.

Downloads GraalVM JDK if needed, runs the Gradle native compilation, and copies
build artifacts to the locations expected by cargo and the Python bindings.
Called from build.rs — uses only Python stdlib (no pip dependencies).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

GRAALVM_URLS: dict[tuple[str, str], dict[str, str]] = {
    ("windows", "x86_64"): {
        "url": "https://github.com/graalvm/graalvm-ce-builds/releases/download/jdk-23.0.1/graalvm-community-jdk-23.0.1_windows-x64_bin.zip",
        "main_dir": "graalvm-community-openjdk-23.0.1+11.1",
    },
    ("macos", "x86_64"): {
        "url": "https://github.com/bell-sw/LibericaNIK/releases/download/24.1.1+1-23.0.1+13/bellsoft-liberica-vm-full-openjdk23.0.1+13-24.1.1+1-macos-amd64.tar.gz",
        "main_dir": "bellsoft-liberica-vm-full-openjdk23-24.1.1/Contents/Home",
    },
    ("macos", "aarch64"): {
        "url": "https://github.com/bell-sw/LibericaNIK/releases/download/24.1.1+1-23.0.1+13/bellsoft-liberica-vm-openjdk23.0.1+13-24.1.1+1-macos-aarch64.tar.gz",
        "main_dir": "bellsoft-liberica-vm-openjdk23-24.1.1/Contents/Home",
    },
    ("linux", "x86_64"): {
        "url": "https://github.com/graalvm/graalvm-ce-builds/releases/download/jdk-23.0.1/graalvm-community-jdk-23.0.1_linux-x64_bin.tar.gz",
        "main_dir": "graalvm-community-openjdk-23.0.1+11.1",
    },
    ("linux", "aarch64"): {
        "url": "https://github.com/graalvm/graalvm-ce-builds/releases/download/jdk-23.0.1/graalvm-community-jdk-23.0.1_linux-aarch64_bin.tar.gz",
        "main_dir": "graalvm-community-openjdk-23.0.1+11.1",
    },
}

HEADER_FILES = [
    "graal_isolate_dynamic.h",
    "graal_isolate.h",
    "libtika_native_dynamic.h",
    "libtika_native.h",
]


def info(msg: str) -> None:
    """Print a cargo warning message (visible during build)."""
    print(f"cargo:warning={msg}")


def is_dir_updated(src: Path, dest: Path) -> bool:
    """Return True if any file in *src* is newer than its counterpart in *dest*."""
    if not dest.exists():
        return True
    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        dest_file = dest / src_file.relative_to(src)
        if not dest_file.exists():
            return True
        try:
            if src_file.stat().st_mtime > dest_file.stat().st_mtime:
                return True
        except OSError:
            return True
    return False


def find_already_built_libs(out_dir: Path) -> Path | None:
    """Search sibling cargo build directories for existing tika-native artifacts."""
    build_dir = out_dir.parent.parent  # e.g. target/debug/build
    if not build_dir.is_dir():
        return None
    for entry in build_dir.iterdir():
        if not entry.is_dir() or not entry.name.startswith("iscc-tika-"):
            continue
        libs_dir = entry / "out" / "libs"
        tika_native_dir = entry / "out" / "tika-native"
        if libs_dir.is_dir() and tika_native_dir.is_dir():
            return libs_dir
    return None


def check_graalvm(graalvm_home: Path, target_os: str) -> bool:
    """Return True if *graalvm_home*/bin contains the native-image tool."""
    exe = "native-image.cmd" if target_os == "windows" else "native-image"
    return (graalvm_home / "bin" / exe).exists()


def graalvm_install_help() -> str:
    """Return a help message for manual GraalVM installation."""
    return (
        "We recommend using sdkman to install and manage different JDKs.\n"
        "See https://sdkman.io/usage for more information.\n"
        "You can install graalvm using:\n"
        "  sdk install java 23.0.1-graalce\n"
        "  sdk use java 23.0.1-graalce"
    )


def get_graalvm_home(install_dir: Path, target_os: str, target_arch: str) -> Path:
    """Find a valid GraalVM JDK or download one."""
    # 1. GRAALVM_HOME
    graalvm_home_env = os.environ.get("GRAALVM_HOME")
    if graalvm_home_env:
        path = Path(graalvm_home_env)
        if not check_graalvm(path, target_os):
            sys.exit(
                f"GRAALVM_HOME={graalvm_home_env} is not a valid GraalVM JDK. "
                f"Please ensure native-image is in its bin/ directory.\n{graalvm_install_help()}"
            )
        return path

    # 2. JAVA_HOME (if it happens to be GraalVM)
    java_home_env = os.environ.get("JAVA_HOME")
    if java_home_env:
        path = Path(java_home_env)
        if check_graalvm(path, target_os):
            return path

    # 3. Auto-download
    return install_graalvm(install_dir, target_os, target_arch)


def install_graalvm(install_dir: Path, target_os: str, target_arch: str) -> Path:
    """Download and extract GraalVM CE for the given platform."""
    key = (target_os, target_arch)
    if key not in GRAALVM_URLS:
        sys.exit(f"Unsupported platform: {target_os}/{target_arch}")

    config = GRAALVM_URLS[key]
    url = config["url"]
    main_dir = config["main_dir"]
    graalvm_home = install_dir / main_dir

    if graalvm_home.exists():
        return graalvm_home

    install_dir.mkdir(parents=True, exist_ok=True)
    archive_ext = "zip" if url.endswith(".zip") else "tar.gz"
    archive_path = install_dir / f"graalvm-ce-archive.{archive_ext}"

    # Download (read fully into memory to avoid corrupt partial files)
    if not archive_path.exists():
        info(f"Downloading GraalVM from {url}")
        req = Request(url, headers={"User-Agent": "iscc-tika-build"})
        try:
            with urlopen(req, timeout=300) as resp:
                data = resp.read()
        except Exception as exc:
            sys.exit(f"Failed to download GraalVM JDK from {url}: {exc}")
        archive_path.write_bytes(data)

    # Extract
    info(f"Extracting GraalVM JDK archive {archive_path}")
    if archive_ext == "zip":
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(install_dir)
    else:
        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(install_dir, filter="data") if sys.version_info >= (
                3,
                12,
            ) else tf.extractall(install_dir)  # noqa: E501

    if not graalvm_home.exists():
        sys.exit(
            f"Failed to extract GraalVM: expected directory {graalvm_home} not found"
        )
    return graalvm_home


def copy_build_artifacts(from_path: Path, to_dirs: list[Path], clean: bool) -> None:
    """Copy build artifacts to one or more directories, optionally removing headers."""
    for dest in to_dirs:
        shutil.copytree(from_path, dest, dirs_exist_ok=True)
        if clean:
            for header in HEADER_FILES:
                path = dest / header
                if path.exists():
                    path.unlink()


def gradle_build(
    tika_native_source_dir: Path,
    out_dir: Path,
    libs_out_dir: Path,
    python_bind_dir: Path | None,
    target_os: str,
    target_arch: str,
) -> None:
    """Run the Gradle nativeCompile build for tika-native."""
    jdk_install_dir = out_dir / "graalvm-jdk"
    tika_native_dir = out_dir / "tika-native"

    graalvm_home = get_graalvm_home(jdk_install_dir, target_os, target_arch)
    info(f"Using GraalVM JDK found at {graalvm_home}")
    info("Building tika_native libs this might take a while ... Please be patient!!")

    # Sync source into OUT_DIR (build scripts must not write outside OUT_DIR)
    if is_dir_updated(tika_native_source_dir, tika_native_dir):
        info("Lib tika_native files were updated")
        if tika_native_dir.exists():
            shutil.rmtree(tika_native_dir)

    if not tika_native_dir.is_dir():
        shutil.copytree(tika_native_source_dir, tika_native_dir)

    # Run gradle
    gradlew = "gradlew.bat" if target_os == "windows" else "gradlew"
    gradlew_path = tika_native_dir / gradlew

    env = {**os.environ, "JAVA_HOME": str(graalvm_home)}
    result = subprocess.run(
        [str(gradlew_path), "--no-daemon", "nativeCompile"],
        cwd=str(tika_native_dir),
        env=env,
    )
    if result.returncode != 0:
        sys.exit("Failed to build tika-native")

    # Copy artifacts to cargo link dir (and optionally Python bindings dir)
    build_path = tika_native_dir / "build" / "native" / "nativeCompile"
    copy_to = [libs_out_dir]
    if python_bind_dir and python_bind_dir.is_dir():
        copy_to.append(python_bind_dir)
    copy_build_artifacts(build_path, copy_to, clean=True)

    info("Successfully built libs")


def main() -> None:
    """Entry point — called from build.rs via Command::new("python")."""
    parser = argparse.ArgumentParser(description="Setup tika-native for iscc-tika")
    parser.add_argument("--manifest-dir", required=True, help="CARGO_MANIFEST_DIR")
    parser.add_argument("--out-dir", required=True, help="Cargo OUT_DIR")
    parser.add_argument(
        "--target-os", required=True, help="Target OS (windows|macos|linux)"
    )
    parser.add_argument(
        "--target-arch", required=True, help="Target arch (x86_64|aarch64)"
    )
    parser.add_argument(
        "--python-bind-dir", default=None, help="Python bindings lib directory"
    )
    args = parser.parse_args()

    manifest_dir = Path(args.manifest_dir)
    out_dir = Path(args.out_dir)
    tika_native_source_dir = manifest_dir / "tika-native"
    python_bind_dir = Path(args.python_bind_dir) if args.python_bind_dir else None
    libs_out_dir = out_dir / "libs"
    tika_native_dir = out_dir / "tika-native"

    need_build = False

    # Check if source files were updated
    if is_dir_updated(tika_native_source_dir, tika_native_dir):
        info("Lib tika_native files were updated")
        if libs_out_dir.exists():
            shutil.rmtree(libs_out_dir)
        if tika_native_dir.exists():
            shutil.rmtree(tika_native_dir)
        need_build = True
    else:
        info("Lib tika_native files were not updated")

    # Try to reuse artifacts from a sibling build directory
    found = find_already_built_libs(out_dir)
    if found is not None:
        if found != libs_out_dir:
            copy_build_artifacts(found, [libs_out_dir], clean=False)
    else:
        need_build = True

    if need_build:
        gradle_build(
            tika_native_source_dir,
            out_dir,
            libs_out_dir,
            python_bind_dir,
            args.target_os,
            args.target_arch,
        )


if __name__ == "__main__":
    main()
