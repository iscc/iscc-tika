import sys

import pytest

from iscc_tika import Extractor, PdfOcrStrategy, PdfParserConfig, TesseractOcrConfig
from utils import cosine_similarity

OCR_DEACTIVATED = pytest.mark.skip(
    reason="OCR tests are deactivated; OCR is opt-in via TesseractOcrConfig().set_skip_ocr(False)"
)


def test_ocr_disabled_by_default_png():
    # Guards deterministic extraction output: even with a Tesseract binary
    # installed, a default Extractor must never OCR images.
    extractor = Extractor()
    result, metadata = extractor.extract_file_to_string(
        "../../test_files/documents/ara-ocr.png"
    )

    assert result.strip() == ""


def test_ocr_disabled_by_default_pdf():
    # Guards deterministic extraction output: a default Extractor must never
    # OCR scanned PDF pages, regardless of the environment.
    extractor = Extractor()
    result, metadata = extractor.extract_file_to_string(
        "../../test_files/documents/deu-ocr.pdf"
    )

    assert result.strip() == ""


@OCR_DEACTIVATED
@pytest.mark.timeout(660)
def test_ara_ocr_png():
    # OCR duration is hardware-dependent; allow slow machines to finish
    ocr_config = (
        TesseractOcrConfig()
        .set_skip_ocr(False)
        .set_language("ara")
        .set_timeout_seconds(600)
    )
    extractor = Extractor().set_ocr_config(ocr_config)
    result, metadata = extractor.extract_file_to_string(
        "../../test_files/documents/ara-ocr.png"
    )

    with open(
        "../../test_files/expected_result/ara-ocr.png.txt", "r", encoding="utf8"
    ) as file:
        expected = file.read()

    assert cosine_similarity(result, expected) > 0.9


@OCR_DEACTIVATED
@pytest.mark.timeout(660)
def test_extract_file_to_string_ocr_only_strategy_deu_ocr_pdf():
    test_file = "../../test_files/documents/deu-ocr.pdf"
    expected_result_file = "../../test_files/expected_result/deu-ocr.pdf.txt"

    pdf_config = PdfParserConfig().set_ocr_strategy(PdfOcrStrategy.OCR_ONLY)
    # OCR duration is hardware-dependent; allow slow machines to finish
    ocr_config = (
        TesseractOcrConfig()
        .set_skip_ocr(False)
        .set_language("deu")
        .set_timeout_seconds(600)
    )

    # Note builder patter is used
    extractor = Extractor()
    extractor = extractor.set_ocr_config(ocr_config)
    extractor = extractor.set_pdf_config(pdf_config)

    result, metadata = extractor.extract_file_to_string(test_file)

    with open(expected_result_file, "r", encoding="utf8") as file:
        expected = file.read()

    assert cosine_similarity(result, expected) > 0.9


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="Test not supported on Windows"
)
def test_test_extract_file_to_string_no_ocr_strategy_deu_ocr_pdf():
    test_file = "../../test_files/documents/deu-ocr.pdf"

    pdf_config = PdfParserConfig()
    pdf_config = pdf_config.set_ocr_strategy(PdfOcrStrategy.NO_OCR)
    ocr_config = TesseractOcrConfig()
    ocr_config = ocr_config.set_language("deu")

    extractor = Extractor().set_ocr_config(ocr_config).set_pdf_config(pdf_config)

    result, metadata = extractor.extract_file_to_string(test_file)

    assert result.strip() == ""
