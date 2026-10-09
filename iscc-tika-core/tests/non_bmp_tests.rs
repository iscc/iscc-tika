//! Regression tests for characters outside the Basic Multilingual Plane (emoji, CJK extension
//! ideographs, musical symbols) in extracted text and metadata, and for truncation at the
//! string length limit, which counts UTF-16 code units and can split such a character.

use iscc_tika::{Extractor, WRITE_LIMIT_REACHED};

/// 😀 U+1F600, 𠀋 U+2000B (CJK Extension B), 𝄞 U+1D11E, plus BMP é and 一.
const MARKER: &str = "Hello é一 😀𠀋𝄞";

const NON_BMP_TXT: &str = "../test_files/documents/non-bmp.txt";

/// Plain text keeps every supplementary character and is not flagged as truncated.
#[test]
fn test_non_bmp_plain_text_round_trip() {
    let (text, metadata) = Extractor::new()
        .extract_file_to_string(NON_BMP_TXT)
        .unwrap();
    // Tika strips the UTF-8 BOM and terminates the extracted text with a newline.
    assert_eq!(text, format!("{MARKER}\n"));
    assert!(!metadata.contains_key(WRITE_LIMIT_REACHED));
}

/// HTML body text and title keep every supplementary character.
#[test]
fn test_non_bmp_html_text_and_title() {
    let (text, metadata) = Extractor::new()
        .extract_file_to_string("../test_files/documents/non-bmp.html")
        .unwrap();
    assert_eq!(text, format!("Body {MARKER}\n"));
    let title = metadata.get("dc:title").expect("html dc:title");
    assert_eq!(title.as_slice(), [format!("Title {MARKER}")]);
}

/// DOCX body text and title keep every supplementary character, also in metadata-only mode.
#[test]
fn test_non_bmp_docx_text_and_title() {
    let extractor = Extractor::new();
    let (text, metadata) = extractor
        .extract_file_to_string("../test_files/documents/non-bmp.docx")
        .unwrap();
    assert_eq!(text, format!("Body {MARKER}\n"));
    let title = metadata.get("dc:title").expect("docx dc:title");
    assert_eq!(title.as_slice(), [format!("Title {MARKER}")]);

    let meta_only = extractor
        .extract_file_metadata("../test_files/documents/non-bmp.docx")
        .unwrap();
    let title_only = meta_only
        .get("dc:title")
        .expect("docx metadata-only dc:title");
    assert_eq!(title_only.as_slice(), [format!("Title {MARKER}")]);
}

/// A limit that splits 𠀋 (UTF-16 units 12 and 13) drops the dangling high surrogate instead
/// of garbling the text, and flags the truncation.
#[test]
fn test_truncation_inside_surrogate_pair() {
    let (text, metadata) = Extractor::new()
        .set_extract_string_max_length(12)
        .extract_file_to_string(NON_BMP_TXT)
        .unwrap();
    assert_eq!(text, "Hello é一 😀");
    assert_eq!(metadata[WRITE_LIMIT_REACHED], ["true"]);
}

/// A limit on a character boundary keeps the full surrogate pair before it.
#[test]
fn test_truncation_at_character_boundary() {
    let (text, metadata) = Extractor::new()
        .set_extract_string_max_length(11)
        .extract_file_to_string(NON_BMP_TXT)
        .unwrap();
    assert_eq!(text, "Hello é一 😀");
    assert_eq!(metadata[WRITE_LIMIT_REACHED], ["true"]);
}

/// Any negative limit disables truncation.
#[test]
fn test_negative_limit_disables_truncation() {
    for limit in [-1, -5, i32::MIN] {
        let (text, metadata) = Extractor::new()
            .set_extract_string_max_length(limit)
            .extract_file_to_string(NON_BMP_TXT)
            .unwrap();
        assert_eq!(text, format!("{MARKER}\n"), "limit {limit}");
        assert!(!metadata.contains_key(WRITE_LIMIT_REACHED), "limit {limit}");
    }
}

/// Metadata-only extraction skips text with a zero limit but does not report it as truncation.
#[test]
fn test_metadata_only_is_not_flagged_as_truncated() {
    let extractor = Extractor::new();
    let from_file = extractor.extract_file_metadata(NON_BMP_TXT).unwrap();
    assert!(!from_file.contains_key(WRITE_LIMIT_REACHED));
    let bytes = std::fs::read(NON_BMP_TXT).unwrap();
    let from_bytes = extractor.extract_bytes_metadata(&bytes).unwrap();
    assert!(!from_bytes.contains_key(WRITE_LIMIT_REACHED));
}
