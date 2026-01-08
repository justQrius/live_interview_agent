use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};

const STORAGE_FILE: &str = "api_keys.json";

#[derive(Serialize, Deserialize, Default)]
struct KeyStorage {
    keys: HashMap<String, String>,
}

fn get_storage_path() -> Result<PathBuf, String> {
    let app_data = std::env::var("APPDATA")
        .or_else(|_| std::env::var("HOME"))
        .map_err(|_| "Could not determine app data directory".to_string())?;
    
    let dir = PathBuf::from(app_data).join("live_interview_agent");
    fs::create_dir_all(&dir).map_err(|e| format!("Failed to create storage directory: {}", e))?;
    
    Ok(dir.join(STORAGE_FILE))
}

fn load_storage() -> Result<KeyStorage, String> {
    let path = get_storage_path()?;
    
    if !path.exists() {
        return Ok(KeyStorage::default());
    }
    
    let contents = fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read storage file: {}", e))?;
    
    serde_json::from_str(&contents)
        .map_err(|e| format!("Failed to parse storage file: {}", e))
}

fn save_storage(storage: &KeyStorage) -> Result<(), String> {
    let path = get_storage_path()?;
    let contents = serde_json::to_string_pretty(storage)
        .map_err(|e| format!("Failed to serialize storage: {}", e))?;
    
    fs::write(&path, contents)
        .map_err(|e| format!("Failed to write storage file: {}", e))
}

pub fn store_key(key_name: &str, key: &str) -> Result<(), String> {
    let mut storage = load_storage()?;
    storage.keys.insert(key_name.to_string(), key.to_string());
    save_storage(&storage)?;
    eprintln!("[Fallback] Stored key: {}", key_name);
    Ok(())
}

pub fn retrieve_key(key_name: &str) -> Result<String, String> {
    let storage = load_storage()?;
    storage.keys.get(key_name)
        .cloned()
        .ok_or_else(|| "Key not found".to_string())
}

pub fn delete_key(key_name: &str) -> Result<(), String> {
    let mut storage = load_storage()?;
    storage.keys.remove(key_name);
    save_storage(&storage)?;
    eprintln!("[Fallback] Deleted key: {}", key_name);
    Ok(())
}

pub fn has_key(key_name: &str) -> bool {
    load_storage()
        .ok()
        .and_then(|s| s.keys.get(key_name).cloned())
        .is_some()
}
