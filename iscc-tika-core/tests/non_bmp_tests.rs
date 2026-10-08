use iscc_tika::Extractor;

/// 😀 U+1F600, 𠀋 U+2000B (CJK Extension B), 𝄞 U+1D11E, plus BMP é and 一.
const MARKER: &str = "Hello é一 😀𠀋𝄞";

fn assert_no_replacement(label: &str, text: &str) {
    assert!(
        !text.contains('\u{FFFD}'),
        "{label} contains U+FFFD: {text:?}"
    );
}

#[test]
fn test_non_bmp_plain_text_round_trip() {
    let (text, _) = Extractor::new()
        .extract_file_to_string("../test_files/documents/non-bmp.txt")
        .unwrap();
    // Tika strips the UTF-8 BOM and terminates the extracted text with a newline.
    assert_eq!(text, format!("{MARKER}\n"));
    assert_no_replacement("non-bmp.txt", &text);
}

#[test]
fn test_non_bmp_html_text_and_title() {
    let (text, metadata) = Extractor::new()
        .extract_file_to_string("../test_files/documents/non-bmp.html")
        .unwrap();
    assert_eq!(text, format!("Body {MARKER}\n"));
    let title = metadata.get("dc:title").expect("html dc:title");
    assert_eq!(title.as_slice(), [format!("Title {MARKER}")]);
    assert_no_replacement("non-bmp.html text", &text);
    assert_no_replacement("non-bmp.html title", &title[0]);
}

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
    assert_no_replacement("non-bmp.docx text", &text);
    assert_no_replacement("non-bmp.docx title", &title[0]);
}
