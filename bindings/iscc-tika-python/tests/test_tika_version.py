"""Tests for the TIKA_VERSION constant exported by the Python bindings."""

import re
from pathlib import Path

from iscc_tika import TIKA_VERSION

BUILD_GRADLE = (
    Path(__file__).resolve().parents[3] / "iscc-tika-core/tika-native/build.gradle"
)


def test_tika_version_matches_gradle_build():
    """TIKA_VERSION is the tikaVersion the native library is built with."""
    gradle = BUILD_GRADLE.read_text(encoding="utf-8")
    assert f'def tikaVersion = "{TIKA_VERSION}"' in gradle


def test_tika_version_format():
    """TIKA_VERSION is a plain major.minor.patch string."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", TIKA_VERSION)
