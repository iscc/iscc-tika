use std::os::raw::{c_char, c_void};

use crate::errors::{Error, ExtractResult};
use crate::Metadata;
use jni::errors::jni_error_code_to_result;
use jni::objects::{JByteBuffer, JObject, JObjectArray, JString, JValue, JValueOwned};
use jni::{sys, JNIEnv, JavaVM};

/// Calls a static method and prints any thrown exceptions to stderr
pub fn jni_new_direct_buffer<'local>(
    env: &mut JNIEnv<'local>,
    data: *mut u8,
    len: usize,
) -> ExtractResult<JByteBuffer<'local>> {
    let direct_byte_buffer = unsafe { env.new_direct_byte_buffer(data, len) }
        .map_err(|_e| Error::JniEnvCall("Failed to create direct byte buffer"))?;

    Ok(direct_byte_buffer)
}

/// Calls a static method and prints any thrown exceptions to stderr
pub fn jni_call_static_method<'local>(
    env: &mut JNIEnv<'local>,
    class: &str,
    method: &str,
    signature: &str,
    args: &[JValue],
) -> ExtractResult<JValueOwned<'local>> {
    let call_result = env.call_static_method(class, method, signature, args);
    match call_result {
        Ok(result) => Ok(result),
        Err(error) => match error {
            jni::errors::Error::JavaException => {
                jni_check_exception(env)?;
                Err(Error::JniError(error))
            }
            _ => Err(Error::JniError(error)),
        },
    }
}

/// Calls an object method and prints any thrown exceptions to stderr
pub fn jni_call_method<'local>(
    env: &mut JNIEnv<'local>,
    obj: &JObject<'local>,
    method: &str,
    signature: &str,
    args: &[JValue],
) -> ExtractResult<JValueOwned<'local>> {
    let call_result = env.call_method(obj, method, signature, args);
    match call_result {
        Ok(result) => Ok(result),
        Err(error) => match error {
            jni::errors::Error::JavaException => {
                jni_check_exception(env)?;
                Err(Error::JniError(error))
            }
            _ => Err(Error::JniError(error)),
        },
    }
}

/// creates a new java string from a rust str
pub fn jni_new_string<'local>(env: &mut JNIEnv<'local>, s: &str) -> ExtractResult<JString<'local>> {
    match env.new_string(s) {
        Ok(s) => Ok(s),
        Err(_) => Err(Error::JniEnvCall("Couldn't create Java String")),
    }
}

/// creates a new java string from a rust str and returns it as a JValueOwned
pub fn jni_new_string_as_jvalue<'local>(
    env: &mut JNIEnv<'local>,
    s: &str,
) -> ExtractResult<JValueOwned<'local>> {
    let jstring = jni_new_string(env, s)?;
    //let jstring = env.new_string(s)?;

    Ok(JValueOwned::from(jstring))
}

/// Converts a java string object to a rust string
///
/// Reads the UTF-16 code units and replaces each unpaired surrogate with U+FFFD. The modified
/// UTF-8 of `GetStringUTFChars` cannot be decoded at all once it holds an unpaired surrogate,
/// which would garble every supplementary character of the string.
pub fn jni_jobject_to_string<'local>(
    env: &mut JNIEnv<'local>,
    jobject: JObject<'local>,
) -> ExtractResult<String> {
    if jobject.is_null() {
        return Err(Error::JniError(jni::errors::Error::NullPtr(
            "jni_jobject_to_string",
        )));
    }
    let raw_env = env.get_raw();
    let raw_string = jobject.as_raw();
    // SAFETY: raw_env is the valid environment of the current thread.
    let functions = unsafe { &**raw_env };
    let get_length = functions
        .GetStringLength
        .ok_or(Error::JniEnvCall("JNI GetStringLength unavailable"))?;
    let get_region = functions
        .GetStringRegion
        .ok_or(Error::JniEnvCall("JNI GetStringRegion unavailable"))?;
    // SAFETY: raw_string is a live java.lang.String reference; the region requested is
    // exactly the string's length and the buffer holds that many code units.
    let units = unsafe {
        let length = get_length(raw_env, raw_string);
        let mut units = vec![0u16; length as usize];
        get_region(raw_env, raw_string, 0, length, units.as_mut_ptr());
        units
    };

    Ok(String::from_utf16_lossy(&units))
}

/// Converts a Java String[] to a Rust Vec<String>
pub fn jni_jobject_array_to_vec<'local>(
    env: &mut JNIEnv<'local>,
    array: JObject<'local>,
) -> ExtractResult<Vec<String>> {
    let j_array_string = JObjectArray::from(array);
    let j_array_length = env.get_array_length(&j_array_string)?;

    let mut vec = Vec::with_capacity(j_array_length as usize);

    for i in 0..j_array_length {
        let elem_obj = env.get_object_array_element(&j_array_string, i)?;
        let elem_str = jni_jobject_to_string(env, elem_obj)?;
        vec.push(elem_str);
    }

    Ok(vec)
}

/// Convert a Tika Metadata a Rust Metadata
pub fn jni_tika_metadata_to_rust_metadata<'local>(
    env: &mut JNIEnv<'local>,
    j_tika_metadata_object: JObject<'local>,
) -> ExtractResult<Metadata> {
    let j_names = JObjectArray::from(
        env.call_method(
            &j_tika_metadata_object,
            "names",
            "()[Ljava/lang/String;",
            &[],
        )?
        .l()?,
    );
    let names_length = env.get_array_length(&j_names)?;
    let mut metadata = Metadata::new();
    for i in 0..names_length {
        // Look values up with the Java key itself: a key holding an unpaired surrogate does
        // not survive a round trip through a Rust string.
        let j_name = env.get_object_array_element(&j_names, i)?;
        let j_values = env
            .call_method(
                &j_tika_metadata_object,
                "getValues",
                "(Ljava/lang/String;)[Ljava/lang/String;",
                &[(&j_name).into()],
            )?
            .l()?;
        let values = jni_jobject_array_to_vec(env, j_values)?;
        let name = jni_jobject_to_string(env, j_name)?;
        // Distinct Java keys can decode to the same Rust key; keep the values of both.
        metadata.entry(name).or_default().extend(values);
    }
    Ok(metadata)
}

/// Checks if there is an exception in the jni environment, describes it to
/// the stderr and finally clears it
pub fn jni_check_exception(env: &mut JNIEnv) -> ExtractResult<bool> {
    if env.exception_check()? {
        env.exception_describe()?;
        env.exception_clear()?;
        return Ok(true);
    }
    Ok(false)
}

/// Creates a new graalvm isolate using the invocation api. A [GraalVM isolate](https://medium.com/graalvm/isolates-and-compressed-references-more-flexible-and-efficient-memory-management-for-graalvm-a044cc50b67e) is a disjoint heap
/// that allows multiple tasks in the same VM instance to run independently.
///
/// This function uses the standard JVM invocation API and relies on the jni-sys crate.
/// No need to specify any libraries because the graalvm native image is already
/// linked in by the build script.
pub fn create_vm_isolate() -> JavaVM {
    unsafe {
        let mut vm_options = [
            // Set java.library.path to be able to load libawt.so, which must be in the same dir as libtika_native.so
            sys::JavaVMOption {
                optionString: c"-Djava.library.path=.".as_ptr() as *mut c_char,
                extraInfo: std::ptr::null_mut(),
            },
            // enable awt headless mode
            sys::JavaVMOption {
                optionString: c"-Djava.awt.headless=true".as_ptr() as *mut c_char,
                extraInfo: std::ptr::null_mut(),
            },
        ];

        let mut args = sys::JavaVMInitArgs {
            version: sys::JNI_VERSION_1_8,
            nOptions: vm_options.len() as sys::jint,
            options: vm_options.as_mut_ptr(),
            ignoreUnrecognized: sys::JNI_TRUE,
        };
        let mut ptr: *mut sys::JavaVM = std::ptr::null_mut();
        let mut env: *mut sys::JNIEnv = std::ptr::null_mut();

        // The current thread becomes the main thread
        let jni_res = sys::JNI_CreateJavaVM(
            &mut ptr as *mut _,
            &mut env as *mut *mut sys::JNIEnv as *mut *mut c_void,
            &mut args as *mut sys::JavaVMInitArgs as *mut c_void,
        );
        jni_error_code_to_result(jni_res).unwrap_or_else(|e| {
            panic!("Failed creating the graal native vm: {:?}", e);
        });

        // This sys call already attaches the current thread to the vm
        JavaVM::from_raw(ptr).unwrap_or_else(|e| {
            panic!("Failed creating the graal native from pointer: {:?}", e);
        })
    }
}

// fn cleanup_vm_isolate(jvm: JavaVM) -> ExtractResult<()>  {
//     println!("cleanup_vm_isolate");
//     // let mut env = jvm.attach_current_thread_as_daemon()?;
//     //
//     // let x = JValue::from(1);
//     // let system_class = env.find_class("java/lang/System")?;
//     // let exit_mid = env.get_static_method_id(&system_class, "exit", "(I)V")?;
//     // let _val = unsafe {
//     //     env.call_static_method_unchecked(
//     //         &system_class,
//     //         exit_mid,
//     //         ReturnType::Primitive(Primitive::Void),
//     //         &[x.as_jni()],
//     //     )
//     // };
//
//     // Destroy jvm. jvm must be dropped as well
//     unsafe {  jvm.destroy()?; }
//     drop(jvm);
//
//     Ok(())
// }

// pub fn tika_parse_file_new_vm(file_name: &str) -> ExtractResult<String> {
//
//     let mut output = String::new();
//
//     let mut start_time = Instant::now();
//     let jvm = create_vm_isolate();
//     let jvm_create_duration = start_time.elapsed();
//
//     start_time = Instant::now();
//     // Need to create a new scope to be able to drop intermediate objects before destroying the jvm
//     {
//         //let mut env = jvm.get_env()?;
//         let mut env = jvm.attach_current_thread()?;
//
//         let jstr_file = env.new_string(file_name)?;
//         let val = env.call_static_method("io/iscc/tika/TikaNativeMain", "parseToString",
//                                          "(Ljava/lang/String;)Ljava/lang/String;", &[JValue::from(&jstr_file)])?;
//
//         let jobject = val.l()?;
//         let jstr_output = JString::from(jobject);
//         let javastr_output = env.get_string(&jstr_output)?;
//         let output_str = javastr_output.to_str().map_err(|e| Error::Utf8Error(e))?;
//         // Creates the string before cleaning the vm
//         output.push_str(output_str);
//     }
//     let parse_duration = start_time.elapsed();
//
//     start_time = Instant::now();
//     cleanup_vm_isolate(jvm)?;
//     let jvm_destroy_duration = start_time.elapsed();
//
//     println!("Time taken to jvm_create_duration: {:.4?}", jvm_create_duration);
//     println!("Time taken to parse_duration: {:.4?}", parse_duration);
//     println!("Time taken to jvm_destroy_duration: {:.4?}", jvm_destroy_duration);
//
//     Ok(output)
// }

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tika::parse::vm;

    /// Creates a Java string from raw UTF-16 code units, which may hold unpaired surrogates.
    fn new_utf16_string<'local>(env: &mut JNIEnv<'local>, units: &[u16]) -> JObject<'local> {
        let raw_env = env.get_raw();
        let new_string = unsafe { (**raw_env).NewString }.unwrap();
        let length = units.len() as sys::jsize;
        unsafe { JObject::from_raw(new_string(raw_env, units.as_ptr(), length)) }
    }

    /// Passes UTF-16 code units through a Java string and decodes them back.
    fn round_trip(units: &[u16]) -> String {
        let mut env = vm().attach_current_thread().unwrap();
        let j_string = new_utf16_string(&mut env, units);
        jni_jobject_to_string(&mut env, j_string).unwrap()
    }

    #[test]
    fn test_jobject_to_string_keeps_supplementary_characters() {
        let text = "Hello é一 😀𠀋𝄞";
        assert_eq!(round_trip(&text.encode_utf16().collect::<Vec<_>>()), text);
    }

    #[test]
    fn test_jobject_to_string_replaces_only_unpaired_surrogates() {
        let mut units: Vec<u16> = "😀 ".encode_utf16().collect();
        // A lone low surrogate, a space and a trailing lone high surrogate.
        units.extend([0xDC00, 0x20, 0xD83D]);
        assert_eq!(round_trip(&units), "😀 \u{FFFD} \u{FFFD}");
    }

    #[test]
    fn test_jobject_to_string_keeps_nul() {
        assert_eq!(round_trip(&[0x61, 0x00, 0x62]), "a\0b");
    }

    #[test]
    fn test_jobject_to_string_empty() {
        assert_eq!(round_trip(&[]), "");
    }

    #[test]
    fn test_jobject_to_string_rejects_null() {
        let mut env = vm().attach_current_thread().unwrap();
        assert!(jni_jobject_to_string(&mut env, JObject::null()).is_err());
    }
}
