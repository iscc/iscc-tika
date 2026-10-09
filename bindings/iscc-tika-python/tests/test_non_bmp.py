"""Tests for supplementary characters and string length truncation in the Python bindings."""

import pytest
from iscc_tika import WRITE_LIMIT_REACHED, Extractor

MARKER = "Hello é一 😀𠀋𝄞"
NON_BMP_TXT = "../../test_files/documents/non-bmp.txt"


def test_non_bmp_text_round_trip():
    """Plain text keeps every supplementary character and is not flagged as truncated."""
    result, metadata = Extractor().extract_file_to_string(NON_BMP_TXT)
    assert result == f"{MARKER}\n"
    assert WRITE_LIMIT_REACHED not in metadata


def test_non_bmp_html_title():
    """Metadata values keep every supplementary character."""
    _, metadata = Extractor().extract_file_to_string(
        "../../test_files/documents/non-bmp.html"
    )
    assert metadata["dc:title"] == [f"Title {MARKER}"]


@pytest.mark.parametrize("limit", [11, 12])
def test_truncation_keeps_whole_characters(limit):
    """A limit inside or right after a surrogate pair cuts on a whole character and flags it."""
    result, metadata = (
        Extractor()
        .set_extract_string_max_length(limit)
        .extract_file_to_string(NON_BMP_TXT)
    )
    assert result == "Hello é一 😀"
    assert metadata[WRITE_LIMIT_REACHED] == ["true"]


def test_negative_limit_disables_truncation():
    """A negative limit extracts the full text."""
    result, metadata = (
        Extractor()
        .set_extract_string_max_length(-1)
        .extract_file_to_string(NON_BMP_TXT)
    )
    assert result == f"{MARKER}\n"
    assert WRITE_LIMIT_REACHED not in metadata


def test_write_limit_reached_key():
    """The exported key matches Tika's write-limit metadata property."""
    assert WRITE_LIMIT_REACHED == "X-TIKA:EXCEPTION:write_limit_reached"
