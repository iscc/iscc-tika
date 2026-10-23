"""Native-image regression: RAR (junrar) and MS Access (jackcess) parsing.

Both documents come from the Apache Tika test corpus (Apache License 2.0).
"""

import json
from pathlib import Path

import pytest
from iscc_tika import Extractor

RAR = "../../test_files/documents/test-documents.rar"
MDB = "../../test_files/documents/testAccess2_2000.mdb"
METADATA_DIR = (
    Path(__file__).resolve().parents[3]
    / "iscc-tika-core/tika-native/src/main/resources/META-INF/io.iscc.tika"
)
JACKCESS_RESOURCES = "com/healthmarketscience/jackcess/index_*.txt"
RAR_ENTRIES = [
    "testEXCEL.xls",
    "testHTML.html",
    "testOpenOffice2.odt",
    "testPDF.pdf",
    "testPPT.ppt",
    "testRTF.rtf",
    "testTXT.txt",
    "testWORD.doc",
    "testXML.xml",
]


@pytest.mark.parametrize("as_xml", [False, True])
def test_rar_lists_entries(as_xml):
    """Every archive entry name appears in the extracted content."""
    text, metadata = Extractor().set_xml_output(as_xml).extract_file_to_string(RAR)
    for name in RAR_ENTRIES:
        assert f"test-documents/{name}" in text
    assert metadata["Content-Type"][0].startswith("application/x-rar-compressed")


def test_access_text():
    """Column names and cell text of the Access tables are extracted."""
    text, metadata = Extractor().extract_file_to_string(MDB)
    assert "ShortTextField" in text
    assert "over the bold italic dog" in text
    assert metadata["Content-Type"][0].startswith("application/x-msaccess")


def test_access_xml_table():
    """XML output renders Access tables as HTML tables."""
    xml, _ = Extractor().set_xml_output(True).extract_file_to_string(MDB)
    assert "<th>ShortTextField</th>" in xml


@pytest.mark.parametrize("platform", ["windows", "linux", "macos"])
def test_jackcess_resources_registered(platform):
    """Every native build target bundles the jackcess index code files."""
    files = list(METADATA_DIR.glob(f"tika-*-{platform}/reachability-metadata.json"))
    assert len(files) == 1, files
    resources = json.loads(files[0].read_text(encoding="utf-8"))["resources"]
    assert {"glob": JACKCESS_RESOURCES} in resources
