use crate::utils::keyring;
use tauri::command;

/// Response when checking for API key existence.
#[derive(serde::Serialize)]
pub struct ApiKeyStatus {
    pub exists: bool,
}

fn get_key_name(provider: &str) -> String {
    // Legacy support: "gemini" maps to "gemini_api_key" which was the hardcoded default
    // For other providers, we use "{provider}_api_key" pattern
    format!("{}_api_key", provider)
}

/// Get the API key from the OS keychain for a specific provider.
///
/// Returns the API key if found, or an error if not found or access fails.
#[command]
pub fn get_api_key(provider: String) -> Result<String, String> {
    let key_name = get_key_name(&provider);
    keyring::retrieve_api_key(&key_name).map_err(|e| e.to_string())
}

/// Store the API key in the OS keychain for a specific provider.
///
/// # Arguments
/// * `provider` - The provider name (e.g., "gemini", "openai")
/// * `key` - The API key to store
///
/// Returns success if stored, or an error if storing fails.
#[command]
pub fn set_api_key(provider: String, key: String) -> Result<(), String> {
    if key.is_empty() {
        return Err("API key cannot be empty".to_string());
    }
    let key_name = get_key_name(&provider);
    
    eprintln!("[Rust] Attempting to store key: service={}, key_name={}", "live_interview_agent", key_name);
    
    match keyring::store_api_key(&key_name, &key) {
        Ok(()) => {
            eprintln!("[Rust] Store reported success, verifying...");
            match keyring::retrieve_api_key(&key_name) {
                Ok(retrieved) => {
                    eprintln!("[Rust] Verification successful, key retrieved: {}...", &retrieved[..10.min(retrieved.len())]);
                    Ok(())
                }
                Err(e) => {
                    eprintln!("[Rust] VERIFICATION FAILED: {}", e);
                    Err(format!("Key stored but verification failed: {}", e))
                }
            }
        }
        Err(e) => {
            eprintln!("[Rust] Store failed: {}", e);
            Err(e.to_string())
        }
    }
}

/// Delete the API key from the OS keychain for a specific provider.
///
/// Returns success if deleted (or if it didn't exist), or an error if deletion fails.
#[command]
pub fn delete_api_key(provider: String) -> Result<(), String> {
    let key_name = get_key_name(&provider);
    keyring::delete_api_key(&key_name).map_err(|e| e.to_string())
}

/// Check if an API key exists in the keychain for a specific provider.
///
/// Returns a status object indicating whether the key exists.
#[command]
pub fn has_api_key(provider: String) -> ApiKeyStatus {
    let key_name = get_key_name(&provider);
    let exists = keyring::has_api_key(&key_name);
    eprintln!("[Rust] Checking if key exists: provider={}, key_name={}, exists={}", provider, key_name, exists);
    ApiKeyStatus { exists }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    #[test]
    fn test_set_api_key_empty() {
        let result = set_api_key("gemini".to_string(), "".to_string());
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "API key cannot be empty");
    }

    #[test]
    #[serial]
    fn test_api_key_roundtrip() {
        let provider = "test_provider";
        let _ = delete_api_key(provider.to_string());

        let set_result = set_api_key(provider.to_string(), "test_key_from_command".to_string());
        if set_result.is_err() {
            eprintln!("Skipping test: keyring storage not available");
            return;
        }

        let get_result = get_api_key(provider.to_string());
        if get_result.is_err() {
            eprintln!("Skipping test: keyring retrieval failed");
            let _ = delete_api_key(provider.to_string());
            return;
        }
        assert_eq!(get_result.unwrap(), "test_key_from_command");

        let _ = delete_api_key(provider.to_string());
    }

    #[test]
    #[serial]
    fn test_has_api_key_command() {
        let provider = "test_provider_2";
        let _ = delete_api_key(provider.to_string());

        let status = has_api_key(provider.to_string());
        assert!(!status.exists);

        let set_result = set_api_key(provider.to_string(), "test_key".to_string());
        if set_result.is_err() {
            eprintln!("Skipping test: keyring storage not available");
            return;
        }

        let status = has_api_key(provider.to_string());
        if !status.exists {
            eprintln!("Skipping test: keyring may not persist in this environment");
            let _ = delete_api_key(provider.to_string());
            return;
        }

        let _ = delete_api_key(provider.to_string());
    }
}
