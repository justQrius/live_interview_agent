// Module declarations
mod commands;
mod utils;

// Import commands for registration
use commands::{config, sidecar, window};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(
      tauri_plugin_log::Builder::default()
        .level(log::LevelFilter::Info)
        .rotation_strategy(tauri_plugin_log::RotationStrategy::KeepAll)
        .max_file_size(5_000_000) // 5 MB per file
        .build(),
    )
    .invoke_handler(tauri::generate_handler![
      config::get_api_key,
      config::set_api_key,
      config::delete_api_key,
      config::has_api_key,
      window::toggle_screen_invisibility,
      sidecar::start_sidecar,
      sidecar::stop_sidecar,
      sidecar::is_sidecar_running,
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
