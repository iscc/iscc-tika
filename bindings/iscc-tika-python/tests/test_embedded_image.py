"""Regression tests for AWT/ImageIO-dependent extraction paths.

Image metadata extraction routes through javax.imageio.ImageIO, which needs a
JDK with AWT support compiled into the native image. GraalVM CE lacks AWT on
macOS, so wheels built with it crash with NoClassDefFoundError on any document
that reaches ImageParser (see https://github.com/iscc/iscc-tika/issues/8).
"""

from iscc_tika import Extractor


def test_png_metadata_via_imageio():
    """Extracting image metadata initializes javax.imageio.ImageIO."""
    metadata = Extractor().extract_file_metadata(
        "../../test_files/documents/table-multi-row-column-cells.png"
    )

    parsers = metadata.get("X-TIKA:Parsed-By", [])
    assert "org.apache.tika.parser.image.ImageParser" in parsers
    # IIO metadata keys are only present when ImageIO actually parsed the image
    assert "Chroma ColorSpaceType" in metadata
    assert metadata["tiff:ImageWidth"] == ["1377"]


def test_pdf_with_embedded_image_text():
    """A PDF containing a raster image extracts text without crashing."""
    result, metadata = Extractor().extract_file_to_string(
        "../../test_files/documents/embedded-image.pdf"
    )

    assert "Embedded image regression test" in result
    assert metadata["Content-Type"] == ["application/pdf"]


def test_pdf_with_embedded_image_metadata():
    """Metadata-only extraction works on a PDF containing a raster image."""
    metadata = Extractor().extract_file_metadata(
        "../../test_files/documents/embedded-image.pdf"
    )

    assert metadata
    assert metadata["Content-Type"] == ["application/pdf"]
    assert metadata["xmpTPg:NPages"] == ["1"]
