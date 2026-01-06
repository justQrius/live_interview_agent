// Placeholder for Python sidecar lifecycle management
// Will be implemented in Story: Python Sidecar Setup

use tauri::command;

#[command]
pub fn start_sidecar() -> Result<(), String> {
    // TODO: Implement sidecar process spawning
    Err("Not implemented yet".to_string())
}

#[command]
pub fn stop_sidecar() -> Result<(), String> {
    // TODO: Implement sidecar process termination
    Err("Not implemented yet".to_string())
}
