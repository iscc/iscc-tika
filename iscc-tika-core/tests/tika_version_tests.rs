//! Tests for the `TIKA_VERSION` constant that build.rs reads from tika-native/build.gradle.
use iscc_tika::TIKA_VERSION;
use std::fs;

#[test]
fn test_tika_version_matches_gradle_build() {
    let gradle = fs::read_to_string("tika-native/build.gradle").unwrap();
    assert!(gradle.contains(&format!("def tikaVersion = \"{TIKA_VERSION}\"")));
}

#[test]
fn test_tika_version_is_three_numbers() {
    let parts: Vec<&str> = TIKA_VERSION.split('.').collect();
    assert_eq!(parts.len(), 3, "unexpected Tika version {TIKA_VERSION:?}");
    assert!(
        parts.iter().all(|p| p.parse::<u32>().is_ok()),
        "unexpected Tika version {TIKA_VERSION:?}"
    );
}
