use tauri::Window;

#[cfg(target_os = "windows")]
pub fn apply_screen_invisibility(window: &Window, enabled: bool) -> Result<(), String> {
    use windows::Win32::Foundation::HWND;
    use windows::Win32::UI::WindowsAndMessaging::{
        SetWindowDisplayAffinity, WDA_EXCLUDEFROMCAPTURE, WDA_NONE,
    };

    let hwnd = window
        .hwnd()
        .map_err(|e| format!("Failed to get window handle: {}", e))?;
    
    let affinity = if enabled {
        WDA_EXCLUDEFROMCAPTURE
    } else {
        WDA_NONE
    };

    unsafe {
        SetWindowDisplayAffinity(HWND(hwnd.0 as *mut _), affinity)
            .map_err(|e| format!("SetWindowDisplayAffinity failed: {}", e))?;
    }
    
    Ok(())
}

#[cfg(target_os = "macos")]
pub fn apply_screen_invisibility(window: &Window, enabled: bool) -> Result<(), String> {
    use cocoa::appkit::NSWindow;
    use cocoa::base::id;
    use objc::{msg_send, sel, sel_impl};

    let ns_window = window
        .ns_window()
        .map_err(|e| format!("Failed to get NSWindow: {}", e))?;

    unsafe {
        let sharing_type: i64 = if enabled { 0 } else { 1 };
        let _: () = msg_send![ns_window as id, setSharingType: sharing_type];
    }

    Ok(())
}

#[cfg(target_os = "linux")]
pub fn apply_screen_invisibility(_window: &Window, enabled: bool) -> Result<(), String> {
    if enabled {
        log::warn!("Screen invisibility on Linux requires Wayland-specific implementation or may not be fully supported on X11");
    }
    Ok(())
}

#[cfg(not(any(target_os = "windows", target_os = "macos", target_os = "linux")))]
pub fn apply_screen_invisibility(_window: &Window, _enabled: bool) -> Result<(), String> {
    Err("Screen invisibility not supported on this platform".to_string())
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_platform_detection() {
        #[cfg(target_os = "windows")]
        assert!(cfg!(target_os = "windows"));
        
        #[cfg(target_os = "macos")]
        assert!(cfg!(target_os = "macos"));
        
        #[cfg(target_os = "linux")]
        assert!(cfg!(target_os = "linux"));
    }
}
