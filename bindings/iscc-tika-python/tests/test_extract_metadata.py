"""Tests for metadata-only extraction (extract_*_metadata).

Best-effort contract: the method runs, returns a non-empty dict, and Content-Type
is populated. No parity with extract_file_to_string is asserted; see the method
docstring for details.
"""

import pytest

from iscc_tika import Extractor
from utils import read_file_to_bytearray

TEST_CASES = [
    "2022_Q3_AAPL.pdf",
    "science-exploration-1p.pptx",
    "simple.odt",
    "table-multi-row-column-cells-actual.csv",
    "vodafone.xlsx",
    "category-level.docx",
    "simple.doc",
    "simple.pptx",
    "table-multi-row-column-cells.png",
    "winter-sports.epub",
    "bug_16.docx",
]


@pytest.mark.parametrize("file_name", TEST_CASES)
def test_extract_file_metadata(file_name):
    path = f"../../test_files/documents/{file_name}"
    metadata = Extractor().extract_file_metadata(path)

    assert isinstance(metadata, dict)
    assert metadata, f"metadata should not be empty for {file_name}"
    assert "Content-Type" in metadata, f"Content-Type missing for {file_name}"


@pytest.mark.parametrize("file_name", TEST_CASES)
def test_extract_bytes_metadata(file_name):
    path = f"../../test_files/documents/{file_name}"
    data = read_file_to_bytearray(path)
    metadata = Extractor().extract_bytes_metadata(data)

    assert isinstance(metadata, dict)
    assert metadata, f"metadata should not be empty for {file_name}"
    assert "Content-Type" in metadata, f"Content-Type missing for {file_name}"


def test_extract_url_metadata():
    metadata = Extractor().extract_url_metadata("https://www.google.com/")

    assert isinstance(metadata, dict)
    assert metadata
    assert "Content-Type" in metadata
