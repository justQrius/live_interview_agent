// Module declarations
mod commands;
mod utils;

// Import commands for registration
use commands::{config, sidecar, window};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      config::get_api_key,
      config::set_api_key,
      config::delete_api_key,
      config::has_api_key,
      window::toggle_screen_invisibility,
      sidecar::start_sidecar,
      sidecar::stop_sidecar,
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
