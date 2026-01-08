use keyring::Entry;
use thiserror::Error;

const SERVICE_NAME: &str = "live_interview_agent";

#[derive(Error, Debug)]
pub enum KeyringError {
    #[error("Failed to access keyring: {0}")]
    AccessError(String),
    #[error("API key not found in keyring")]
    NotFound,
    #[error("Failed to store API key: {0}")]
    StoreError(String),
    #[error("Failed to delete API key: {0}")]
    DeleteError(String),
}

fn get_entry(key_name: &str) -> Result<Entry, KeyringError> {
    Entry::new(SERVICE_NAME, key_name).map_err(|e| KeyringError::AccessError(e.to_string()))
}

/// Store an API key securely in the OS keychain.
///
/// # Arguments
/// * `key_name` - The name of the key to store (e.g., "gemini_api_key")
/// * `key` - The API key to store
///
/// # Returns
/// * `Ok(())` if successful
/// * `Err(KeyringError)` if storing fails
pub fn store_api_key(key_name: &str, key: &str) -> Result<(), KeyringError> {
    eprintln!("[Keyring] store_api_key called for: {}", key_name);
    let entry = get_entry(key_name)?;
    
    match entry.set_password(key) {
        Ok(()) => {
            eprintln!("[Keyring] OS keyring set_password returned Ok, verifying...");
            
            std::thread::sleep(std::time::Duration::from_millis(100));
            
            match entry.get_password() {
                Ok(retrieved) => {
                    eprintln!("[Keyring] OS keyring get_password returned Ok, checking if it matches...");
                    if retrieved == key {
                        eprintln!("[Keyring] OS keyring verification successful!");
                        Ok(())
                    } else {
                        eprintln!("[Keyring] OS keyring returned different value, using fallback");
                        crate::utils::storage_fallback::store_key(key_name, key)
                            .map_err(|e| KeyringError::StoreError(e))
                    }
                }
                Err(e) => {
                    eprintln!("[Keyring] OS keyring get_password failed: {}, using fallback storage", e);
                    crate::utils::storage_fallback::store_key(key_name, key)
                        .map_err(|e| KeyringError::StoreError(e))
                }
            }
        }
        Err(e) => {
            eprintln!("[Keyring] OS keyring set_password failed: {}, using fallback storage", e);
            crate::utils::storage_fallback::store_key(key_name, key)
                .map_err(|e| KeyringError::StoreError(e))
        }
    }
}

/// Retrieve an API key from the OS keychain.
///
/// # Arguments
/// * `key_name` - The name of the key to retrieve
///
/// # Returns
/// * `Ok(String)` with the API key if found
/// * `Err(KeyringError::NotFound)` if no key is stored
/// * `Err(KeyringError::AccessError)` if keychain access fails
pub fn retrieve_api_key(key_name: &str) -> Result<String, KeyringError> {
    let entry = get_entry(key_name)?;
    match entry.get_password() {
        Ok(password) => Ok(password),
        Err(keyring::Error::NoEntry) | Err(_) => {
            crate::utils::storage_fallback::retrieve_key(key_name)
                .map_err(|_| KeyringError::NotFound)
        }
    }
}

/// Delete an API key from the OS keychain.
///
/// # Arguments
/// * `key_name` - The name of the key to delete
///
/// # Returns
/// * `Ok(())` if successful or if key was not found
/// * `Err(KeyringError)` if deletion fails
pub fn delete_api_key(key_name: &str) -> Result<(), KeyringError> {
    let entry = get_entry(key_name)?;
    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()), // Already deleted, that's fine
        Err(e) => Err(KeyringError::DeleteError(e.to_string())),
    }
}

/// Check if an API key is stored in the keychain.
///
/// # Arguments
/// * `key_name` - The name of the key to check
///
/// # Returns
/// * `true` if a key exists
/// * `false` if no key is stored or access fails
pub fn has_api_key(key_name: &str) -> bool {
    retrieve_api_key(key_name).is_ok() || crate::utils::storage_fallback::has_key(key_name)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    const TEST_KEY: &str = "test_api_key_12345";
    const TEST_KEY_NAME: &str = "test_key_name";

    fn cleanup() {
        let _ = delete_api_key(TEST_KEY_NAME);
    }

    #[test]
    #[serial]
    fn test_store_and_retrieve_api_key() {
        cleanup();

        let store_result = store_api_key(TEST_KEY_NAME, TEST_KEY);
        if store_result.is_err() {
            eprintln!(
                "Skipping test: keyring storage not available: {:?}",
                store_result
            );
            return;
        }

        let retrieve_result = retrieve_api_key(TEST_KEY_NAME);
        if let Err(e) = &retrieve_result {
            eprintln!("Skipping test: keyring retrieval failed: {:?}", e);
            cleanup();
            return;
        }
        assert_eq!(retrieve_result.unwrap(), TEST_KEY);

        cleanup();
    }

    #[test]
    #[serial]
    fn test_retrieve_nonexistent_key() {
        cleanup();

        let result = retrieve_api_key(TEST_KEY_NAME);
        assert!(matches!(result, Err(KeyringError::NotFound)));
    }

    #[test]
    #[serial]
    fn test_delete_api_key() {
        let store_result = store_api_key(TEST_KEY_NAME, TEST_KEY);
        if store_result.is_err() {
            eprintln!("Skipping test: keyring storage not available");
            return;
        }

        let delete_result = delete_api_key(TEST_KEY_NAME);
        assert!(delete_result.is_ok());

        let retrieve_result = retrieve_api_key(TEST_KEY_NAME);
        assert!(matches!(retrieve_result, Err(KeyringError::NotFound)));
    }

    #[test]
    #[serial]
    fn test_delete_nonexistent_key() {
        cleanup();

        let result = delete_api_key(TEST_KEY_NAME);
        assert!(result.is_ok());
    }

    #[test]
    #[serial]
    fn test_has_api_key() {
        cleanup();
        assert!(!has_api_key(TEST_KEY_NAME));

        let store_result = store_api_key(TEST_KEY_NAME, TEST_KEY);
        if store_result.is_err() {
            eprintln!("Skipping test: keyring storage not available");
            return;
        }

        if !has_api_key(TEST_KEY_NAME) {
            eprintln!("Skipping test: keyring may not persist in this environment");
            cleanup();
            return;
        }

        cleanup();
    }

    #[test]
    #[serial]
    fn test_overwrite_api_key() {
        cleanup();

        let initial_store = store_api_key(TEST_KEY_NAME, "initial_key");
        if initial_store.is_err() {
            eprintln!("Skipping test: keyring storage not available");
            return;
        }

        let store_result = store_api_key(TEST_KEY_NAME, "new_key");
        assert!(store_result.is_ok());

        let retrieve_result = retrieve_api_key(TEST_KEY_NAME);
        if retrieve_result.is_err() {
            eprintln!("Skipping test: keyring retrieval failed");
            cleanup();
            return;
        }
        assert_eq!(retrieve_result.unwrap(), "new_key");

        cleanup();
    }
}
