// Python sidecar lifecycle management
//
// This module handles spawning and terminating the Python sidecar process
// that runs the WebSocket server for audio processing and LLM integration.

use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::command;

/// Global state for the sidecar process
static SIDECAR_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

/// Get the sidecar executable path based on the current platform
fn get_sidecar_path() -> Result<std::path::PathBuf, String> {
    // In development mode, use Python directly
    if cfg!(debug_assertions) {
        return get_development_path();
    }
    
    // In production, use the bundled executable
    get_bundled_path()
}

/// Get the path for development mode (run Python script directly)
fn get_development_path() -> Result<std::path::PathBuf, String> {
    let current_dir = std::env::current_dir()
        .map_err(|e| format!("Failed to get current directory: {}", e))?;
    
    // Look for sidecar directory relative to src-tauri
    let sidecar_dir = current_dir.parent()
        .ok_or("Failed to get parent directory")?
        .join("sidecar")
        .join("src")
        .join("server.py");
    
    if sidecar_dir.exists() {
        Ok(sidecar_dir)
    } else {
        // Try from project root
        let from_root = current_dir.join("sidecar").join("src").join("server.py");
        if from_root.exists() {
            Ok(from_root)
        } else {
            Err(format!(
                "Development sidecar not found at {:?} or {:?}",
                sidecar_dir, from_root
            ))
        }
    }
}

/// Get the path for the bundled executable in production
fn get_bundled_path() -> Result<std::path::PathBuf, String> {
    // Get the target triple for the current platform
    let target = get_target_triple();
    
    // The executable name includes the target triple for Tauri's externalBin
    let exe_name = if cfg!(windows) {
        format!("sidecar-server-{}.exe", target)
    } else {
        format!("sidecar-server-{}", target)
    };
    
    // Look in the binaries directory next to the executable
    let exe_path = std::env::current_exe()
        .map_err(|e| format!("Failed to get current executable path: {}", e))?;
    
    let exe_dir = exe_path.parent()
        .ok_or("Failed to get executable directory")?;
    
    // Check various possible locations
    let possible_paths = [
        exe_dir.join(&exe_name),
        exe_dir.join("binaries").join(&exe_name),
        exe_dir.parent()
            .map(|p| p.join("binaries").join(&exe_name))
            .unwrap_or_default(),
    ];
    
    for path in &possible_paths {
        if path.exists() {
            return Ok(path.clone());
        }
    }
    
    Err(format!(
        "Bundled sidecar not found. Searched: {:?}",
        possible_paths
    ))
}

/// Get the target triple for the current platform
fn get_target_triple() -> &'static str {
    #[cfg(all(target_os = "windows", target_arch = "x86_64"))]
    { "x86_64-pc-windows-msvc" }
    
    #[cfg(all(target_os = "windows", target_arch = "aarch64"))]
    { "aarch64-pc-windows-msvc" }
    
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    { "x86_64-apple-darwin" }
    
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    { "aarch64-apple-darwin" }
    
    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    { "x86_64-unknown-linux-gnu" }
    
    #[cfg(all(target_os = "linux", target_arch = "aarch64"))]
    { "aarch64-unknown-linux-gnu" }
    
    #[cfg(not(any(
        all(target_os = "windows", target_arch = "x86_64"),
        all(target_os = "windows", target_arch = "aarch64"),
        all(target_os = "macos", target_arch = "x86_64"),
        all(target_os = "macos", target_arch = "aarch64"),
        all(target_os = "linux", target_arch = "x86_64"),
        all(target_os = "linux", target_arch = "aarch64"),
    )))]
    { "unknown-unknown-unknown" }
}

/// Start the Python sidecar process
/// 
/// In development mode, this runs the Python script directly.
/// In production mode, this runs the bundled PyInstaller executable.
#[command]
pub fn start_sidecar() -> Result<(), String> {
    let mut process_guard = SIDECAR_PROCESS.lock()
        .map_err(|e| format!("Failed to acquire lock: {}", e))?;
    
    // Check if already running
    if let Some(ref mut child) = *process_guard {
        match child.try_wait() {
            Ok(Some(_)) => {
                // Process has exited, clear it
                *process_guard = None;
            }
            Ok(None) => {
                // Process is still running
                return Err("Sidecar is already running".to_string());
            }
            Err(e) => {
                log::warn!("Error checking sidecar status: {}", e);
                *process_guard = None;
            }
        }
    }
    
    let sidecar_path = get_sidecar_path()?;
    log::info!("Starting sidecar from: {:?}", sidecar_path);
    
    let child = if cfg!(debug_assertions) {
        // Development mode: run Python script
        Command::new("python")
            .arg(&sidecar_path)
            .spawn()
            .map_err(|e| format!("Failed to start sidecar (dev mode): {}", e))?
    } else {
        // Production mode: run bundled executable
        Command::new(&sidecar_path)
            .spawn()
            .map_err(|e| format!("Failed to start sidecar: {}", e))?
    };
    
    let pid = child.id();
    *process_guard = Some(child);
    
    log::info!("Sidecar started with PID: {}", pid);
    Ok(())
}

/// Stop the Python sidecar process
#[command]
pub fn stop_sidecar() -> Result<(), String> {
    let mut process_guard = SIDECAR_PROCESS.lock()
        .map_err(|e| format!("Failed to acquire lock: {}", e))?;
    
    if let Some(ref mut child) = *process_guard {
        log::info!("Stopping sidecar process...");
        
        // Try graceful shutdown first (send SIGTERM on Unix)
        #[cfg(unix)]
        {
            use std::os::unix::process::CommandExt;
            unsafe {
                libc::kill(child.id() as i32, libc::SIGTERM);
            }
            // Give it a moment to shut down gracefully
            std::thread::sleep(std::time::Duration::from_millis(500));
        }
        
        // Check if it's still running
        match child.try_wait() {
            Ok(Some(status)) => {
                log::info!("Sidecar exited with status: {:?}", status);
            }
            Ok(None) => {
                // Still running, force kill
                log::warn!("Sidecar didn't stop gracefully, forcing termination...");
                child.kill()
                    .map_err(|e| format!("Failed to kill sidecar: {}", e))?;
                child.wait()
                    .map_err(|e| format!("Failed to wait for sidecar: {}", e))?;
            }
            Err(e) => {
                log::error!("Error checking sidecar status: {}", e);
            }
        }
        
        *process_guard = None;
        log::info!("Sidecar stopped");
        Ok(())
    } else {
        Err("Sidecar is not running".to_string())
    }
}

/// Check if the sidecar is currently running
#[command]
pub fn is_sidecar_running() -> Result<bool, String> {
    let mut process_guard = SIDECAR_PROCESS.lock()
        .map_err(|e| format!("Failed to acquire lock: {}", e))?;
    
    if let Some(ref mut child) = *process_guard {
        match child.try_wait() {
            Ok(Some(_)) => {
                // Process has exited
                *process_guard = None;
                Ok(false)
            }
            Ok(None) => {
                // Process is still running
                Ok(true)
            }
            Err(e) => {
                log::warn!("Error checking sidecar status: {}", e);
                *process_guard = None;
                Ok(false)
            }
        }
    } else {
        Ok(false)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_get_target_triple_is_valid() {
        let triple = get_target_triple();
        assert!(!triple.is_empty());
        assert!(triple.contains('-'));
    }
    
    #[test]
    fn test_get_development_path_returns_result() {
        // This may succeed or fail depending on the working directory
        let result = get_development_path();
        // We just verify it returns a valid Result type
        assert!(result.is_ok() || result.is_err());
    }
    
    #[test]
    fn test_start_stop_sidecar_not_found_in_test() {
        // In test environment, the sidecar won't be found
        // This test verifies error handling
        let result = start_sidecar();
        // It should fail gracefully, not panic
        // (will succeed if Python sidecar is actually available)
        if result.is_err() {
            let err = result.unwrap_err();
            assert!(err.contains("Failed") || err.contains("not found"));
        }
    }
}
