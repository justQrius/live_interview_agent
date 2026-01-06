use crate::utils::platform;
use tauri::{command, Window};

#[command]
pub fn toggle_screen_invisibility(window: Window, enabled: bool) -> Result<(), String> {
    platform::apply_screen_invisibility(&window, enabled)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_toggle_screen_invisibility_compiles() {
        let _ = toggle_screen_invisibility;
    }
}
