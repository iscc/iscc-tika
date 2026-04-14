// Expose the iscc-tika rust core as `ecore`.
// We will use `ecore::Xxx` to represents all types from iscc-tika rust core.
pub use ::iscc_tika as ecore;
use pyo3::prelude::*;

// Modules
mod extractor;
pub use extractor::*;
mod config;
pub use config::*;

/// iscc-tika is a library that extracts text from various file formats.
/// * Supports many file formats such as Word, Excel, PowerPoint, PDF, and many more.
/// * Strives to be simple fast and efficient
///
///
/// ### Usage
///
/// * Extracting a file to string:
///
/// ```python
/// from iscc_tika import Extractor
///
/// extractor = Extractor()
/// extractor.set_extract_string_max_length(1000)
/// result = extractor.extract_file_to_string("README.md")
///
/// print(result)
/// ```
///
/// * Extracting a file to a buffered stream:
///
/// ```python
/// from iscc_tika import Extractor
///
/// extractor = Extractor()
/// reader = extractor.extract_file("tests/quarkus.pdf")
///
/// result = ""
/// buffer = reader.read(4096)
/// while len(buffer) > 0:
/// result += buffer.decode("utf-8")
/// buffer = reader.read(4096)
///
/// print(result)
/// ```

// The name of this function must match the `lib.name` setting in the `Cargo.toml`,
// otherwise Python will not be able to import the module.
#[pymodule]
fn _iscc_tika(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CharSet>()?;
    m.add_class::<StreamReader>()?;
    m.add_class::<Extractor>()?;

    // Config
    m.add_class::<PdfOcrStrategy>()?;
    m.add_class::<PdfParserConfig>()?;
    m.add_class::<OfficeParserConfig>()?;
    m.add_class::<TesseractOcrConfig>()?;

    Ok(())
}
