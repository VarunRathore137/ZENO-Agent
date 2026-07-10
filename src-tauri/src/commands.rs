use tauri::AppHandle;

/// Returns the base URL of the Python FastAPI daemon.
/// The React frontend uses this as its API root.
#[tauri::command]
pub fn get_api_base() -> String {
    "http://127.0.0.1:8766".to_string()
}

/// Shows the overlay quick-capture window.
#[tauri::command]
pub fn show_overlay_window(app: AppHandle) -> Result<(), String> {
    use tauri::Manager;
    if let Some(win) = app.get_webview_window("overlay") {
        win.show().map_err(|e| e.to_string())?;
        win.set_focus().map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Hides the overlay quick-capture window.
#[tauri::command]
pub fn hide_overlay_window(app: AppHandle) -> Result<(), String> {
    use tauri::Manager;
    if let Some(win) = app.get_webview_window("overlay") {
        win.hide().map_err(|e| e.to_string())?;
    }
    Ok(())
}
