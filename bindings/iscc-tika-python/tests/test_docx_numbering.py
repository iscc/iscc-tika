"""Native-image regression: XMLBeans must construct CTNumLvlImpl for lvlOverride."""

import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from iscc_tika import Extractor

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
METADATA_DIR = (
    Path(__file__).resolve().parents[3]
    / "iscc-tika-core/tika-native/src/main/resources/META-INF/io.iscc.tika"
)


def numbering_docx(override):
    """Small self-contained document; no copied public document or image assets."""
    parts = {
        "[Content_Types].xml": """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
          <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
        </Types>""",
        "_rels/.rels": """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
        </Relationships>""",
        "word/_rels/document.xml.rels": """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
        </Relationships>""",
        "word/document.xml": f'''<w:document xmlns:w="{W}"><w:body>
          <w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>First numbered item</w:t></w:r></w:p>
          <w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>Second numbered item</w:t></w:r></w:p>
          <w:sectPr/>
        </w:body></w:document>''',
        "word/numbering.xml": f'''<w:numbering xmlns:w="{W}">
          <w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum>
          <w:num w:numId="1"><w:abstractNumId w:val="0"/>{override}</w:num>
        </w:numbering>''',
    }
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, text in parts.items():
            archive.writestr(name, text.encode("utf-8"))
    return output.getvalue()


@pytest.mark.parametrize(
    "override",
    [
        "",
        '<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride>',
        '<w:lvlOverride w:ilvl="0"><w:startOverride w:val="5"/></w:lvlOverride>',
        '<w:lvlOverride w:ilvl="0"><w:lvl w:ilvl="0"><w:start w:val="3"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:lvlOverride>',
        '<w:lvlOverride w:ilvl="0"/>',
    ],
)
@pytest.mark.parametrize("as_xml", [False, True])
def test_docx_numbering_overrides(override, as_xml, tmp_path):
    """Numbered DOCX text extracts with and without lvlOverride, from file and bytes."""
    data = numbering_docx(override)
    path = tmp_path / "numbering-overrides.docx"
    path.write_bytes(data)
    extractor = Extractor().set_xml_output(as_xml)
    for text, metadata in (
        extractor.extract_file_to_string(str(path)),
        extractor.extract_bytes_to_string(bytearray(data)),
    ):
        assert "First numbered item" in text
        assert "Second numbered item" in text
        assert metadata["Content-Type"] == [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]


@pytest.mark.parametrize("platform", ["windows", "linux", "macos"])
def test_numbering_override_constructor_registered(platform):
    """Check every native build target, even when pytest runs on just one OS."""
    files = list(METADATA_DIR.glob(f"tika-*-{platform}/reachability-metadata.json"))
    assert len(files) == 1, files
    entries = json.loads(files[0].read_text(encoding="utf-8"))["reflection"]
    entry = next(
        x
        for x in entries
        if x["type"]
        == "org.openxmlformats.schemas.wordprocessingml.x2006.main.impl.CTNumLvlImpl"
    )
    assert {
        "name": "<init>",
        "parameterTypes": ["org.apache.xmlbeans.SchemaType"],
    } in entry["methods"]
