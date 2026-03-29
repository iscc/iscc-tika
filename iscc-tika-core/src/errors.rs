use std::io;
use std::str::Utf8Error;

/// Represent errors returned by iscc-tika
#[derive(thiserror::Error, Debug)]
pub enum Error {
    #[error("{0}")]
    Unknown(String),

    #[error("{0}")]
    IoError(String),

    #[error("{0}")]
    ParseError(String),

    #[error("{0}")]
    Utf8Error(#[from] Utf8Error),

    #[error("{0}")]
    JniError(#[from] jni::errors::Error),

    #[error("{0}")]
    JniEnvCall(&'static str),
}

// Implement the conversion from our Error type to io::Error
// This allows us to use the ? when implementing std::io traits such as: Read, Write Seek etc ...
impl From<Error> for io::Error {
    fn from(err: Error) -> Self {
        match err {
            Error::IoError(msg) => io::Error::other(format!("Io error: {msg}")),
            Error::ParseError(msg) => io::Error::other(format!("Parse error: {msg}")),
            Error::Utf8Error(e) => io::Error::other(format!("UTF8 error: {e}")),
            Error::JniError(e) => io::Error::other(format!("JNI error: {e}")),
            Error::JniEnvCall(msg) => io::Error::other(format!("JNI env call error: {msg}")),
            _ => io::Error::other("Unknown error"),
        }
    }
}

/// Result that is a wrapper of Result<T, iscc_tika::Error>
pub type ExtractResult<T> = Result<T, Error>;
