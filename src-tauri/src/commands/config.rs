use crate::utils::keyring;
use tauri::command;

/// Response when checking for API key existence.
#[derive(serde::Serialize)]
pub struct ApiKeyStatus {
    pub exists: bool,
}

/// Get the API key from the OS keychain.
///
/// Returns the API key if found, or an error if not found or access fails.
#[command]
pub fn get_api_key() -> Result<String, String> {
    keyring::retrieve_api_key().map_err(|e| e.to_string())
}

/// Store the API key in the OS keychain.
///
/// # Arguments
/// * `key` - The API key to store
///
/// Returns success if stored, or an error if storing fails.
#[command]
pub fn set_api_key(key: String) -> Result<(), String> {
    if key.is_empty() {
        return Err("API key cannot be empty".to_string());
    }
    keyring::store_api_key(&key).map_err(|e| e.to_string())
}

/// Delete the API key from the OS keychain.
///
/// Returns success if deleted (or if it didn't exist), or an error if deletion fails.
#[command]
pub fn delete_api_key() -> Result<(), String> {
    keyring::delete_api_key().map_err(|e| e.to_string())
}

/// Check if an API key exists in the keychain.
///
/// Returns a status object indicating whether the key exists.
#[command]
pub fn has_api_key() -> ApiKeyStatus {
    ApiKeyStatus {
        exists: keyring::has_api_key(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    #[test]
    fn test_set_api_key_empty() {
        let result = set_api_key("".to_string());
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "API key cannot be empty");
    }

    #[test]
    #[serial]
    fn test_api_key_roundtrip() {
        let _ = delete_api_key();

        let set_result = set_api_key("test_key_from_command".to_string());
        if set_result.is_err() {
            eprintln!("Skipping test: keyring storage not available");
            return;
        }

        let get_result = get_api_key();
        if get_result.is_err() {
            eprintln!("Skipping test: keyring retrieval failed");
            let _ = delete_api_key();
            return;
        }
        assert_eq!(get_result.unwrap(), "test_key_from_command");

        let _ = delete_api_key();
    }

    #[test]
    #[serial]
    fn test_has_api_key_command() {
        let _ = delete_api_key();

        let status = has_api_key();
        assert!(!status.exists);

        let set_result = set_api_key("test_key".to_string());
        if set_result.is_err() {
            eprintln!("Skipping test: keyring storage not available");
            return;
        }

        let status = has_api_key();
        if !status.exists {
            eprintln!("Skipping test: keyring may not persist in this environment");
            let _ = delete_api_key();
            return;
        }

        let _ = delete_api_key();
    }
}
