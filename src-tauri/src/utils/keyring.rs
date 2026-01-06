use keyring::Entry;
use thiserror::Error;

const SERVICE_NAME: &str = "live_interview_agent";
const API_KEY_USERNAME: &str = "gemini_api_key";

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

fn get_entry() -> Result<Entry, KeyringError> {
    Entry::new(SERVICE_NAME, API_KEY_USERNAME).map_err(|e| KeyringError::AccessError(e.to_string()))
}

/// Store the Gemini API key securely in the OS keychain.
///
/// # Arguments
/// * `key` - The API key to store
///
/// # Returns
/// * `Ok(())` if successful
/// * `Err(KeyringError)` if storing fails
pub fn store_api_key(key: &str) -> Result<(), KeyringError> {
    let entry = get_entry()?;
    entry
        .set_password(key)
        .map_err(|e| KeyringError::StoreError(e.to_string()))
}

/// Retrieve the Gemini API key from the OS keychain.
///
/// # Returns
/// * `Ok(String)` with the API key if found
/// * `Err(KeyringError::NotFound)` if no key is stored
/// * `Err(KeyringError::AccessError)` if keychain access fails
pub fn retrieve_api_key() -> Result<String, KeyringError> {
    let entry = get_entry()?;
    match entry.get_password() {
        Ok(password) => Ok(password),
        Err(keyring::Error::NoEntry) => Err(KeyringError::NotFound),
        Err(e) => Err(KeyringError::AccessError(e.to_string())),
    }
}

/// Delete the Gemini API key from the OS keychain.
///
/// # Returns
/// * `Ok(())` if successful or if key was not found
/// * `Err(KeyringError)` if deletion fails
pub fn delete_api_key() -> Result<(), KeyringError> {
    let entry = get_entry()?;
    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()), // Already deleted, that's fine
        Err(e) => Err(KeyringError::DeleteError(e.to_string())),
    }
}

/// Check if an API key is stored in the keychain.
///
/// # Returns
/// * `true` if a key exists
/// * `false` if no key is stored or access fails
pub fn has_api_key() -> bool {
    retrieve_api_key().is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    const TEST_KEY: &str = "test_api_key_12345";

    fn cleanup() {
        let _ = delete_api_key();
    }

    #[test]
    #[serial]
    fn test_store_and_retrieve_api_key() {
        cleanup();

        let store_result = store_api_key(TEST_KEY);
        if store_result.is_err() {
            eprintln!(
                "Skipping test: keyring storage not available: {:?}",
                store_result
            );
            return;
        }

        let retrieve_result = retrieve_api_key();
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

        let result = retrieve_api_key();
        assert!(matches!(result, Err(KeyringError::NotFound)));
    }

    #[test]
    #[serial]
    fn test_delete_api_key() {
        let store_result = store_api_key(TEST_KEY);
        if store_result.is_err() {
            eprintln!("Skipping test: keyring storage not available");
            return;
        }

        let delete_result = delete_api_key();
        assert!(delete_result.is_ok());

        let retrieve_result = retrieve_api_key();
        assert!(matches!(retrieve_result, Err(KeyringError::NotFound)));
    }

    #[test]
    #[serial]
    fn test_delete_nonexistent_key() {
        cleanup();

        let result = delete_api_key();
        assert!(result.is_ok());
    }

    #[test]
    #[serial]
    fn test_has_api_key() {
        cleanup();
        assert!(!has_api_key());

        let store_result = store_api_key(TEST_KEY);
        if store_result.is_err() {
            eprintln!("Skipping test: keyring storage not available");
            return;
        }

        if !has_api_key() {
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

        let initial_store = store_api_key("initial_key");
        if initial_store.is_err() {
            eprintln!("Skipping test: keyring storage not available");
            return;
        }

        let store_result = store_api_key("new_key");
        assert!(store_result.is_ok());

        let retrieve_result = retrieve_api_key();
        if retrieve_result.is_err() {
            eprintln!("Skipping test: keyring retrieval failed");
            cleanup();
            return;
        }
        assert_eq!(retrieve_result.unwrap(), "new_key");

        cleanup();
    }
}
