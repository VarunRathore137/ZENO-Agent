use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::TrayIconBuilder,
    Manager, WindowEvent,
};

mod commands;

const API_BASE: &str = "http://127.0.0.1:8766";

fn post_daemon(path: &str) -> Option<serde_json::Value> {
    let url = format!("{API_BASE}{path}");
    reqwest::blocking::Client::new()
        .post(&url)
        .send()
        .ok()
        .and_then(|r| r.json().ok())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            commands::get_api_base,
            commands::show_overlay_window,
            commands::hide_overlay_window,
        ])
        .setup(|app| {
            // Build tray menu
            let open_i    = MenuItemBuilder::with_id("open",     "Open Dashboard").build(app)?;
            let focus_i   = MenuItemBuilder::with_id("focus",    "Toggle Focus Mode").build(app)?;
            let mute_i    = MenuItemBuilder::with_id("mute",     "Mute Voice").build(app)?;
            let sep1      = tauri::menu::PredefinedMenuItem::separator(app)?;
            let quit_i    = MenuItemBuilder::with_id("quit",     "Quit ZENO").build(app)?;

            let menu = MenuBuilder::new(app)
                .items(&[&open_i, &focus_i, &mute_i, &sep1, &quit_i])
                .build()?;

            TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .tooltip("ZENO — Your Personal AI Assistant")
                .show_menu_on_left_click(false)
                .on_tray_icon_event(|tray, event| {
                    // Left click: toggle main window
                    if let tauri::tray::TrayIconEvent::Click { .. } = event {
                        let app = tray.app_handle();
                        if let Some(win) = app.get_webview_window("main") {
                            if win.is_visible().unwrap_or(false) {
                                let _ = win.hide();
                            } else {
                                let _ = win.show();
                                let _ = win.set_focus();
                            }
                        }
                    }
                })
                .on_menu_event(move |app, event| match event.id().as_ref() {
                    "open" => {
                        if let Some(win) = app.get_webview_window("main") {
                            let _ = win.show();
                            let _ = win.set_focus();
                        }
                    }
                    "focus" => {
                        if let Some(resp) = post_daemon("/daemon/focus") {
                            // Update menu label dynamically
                            let label = resp["label"].as_str().unwrap_or("Toggle Focus Mode");
                            if let Some(win) = app.get_webview_window("main") {
                                let _ = win.emit("daemon_state", &resp);
                            }
                            // Note: Tauri 2 does not support dynamic menu item label updates
                            // via MenuItem.set_text() in the on_menu_event closure due to
                            // ownership constraints. State is pushed to frontend via emit() instead.
                            let _ = label; // suppress unused warning
                        }
                    }
                    "mute" => {
                        if let Some(resp) = post_daemon("/daemon/tts/mute") {
                            if let Some(win) = app.get_webview_window("main") {
                                let _ = win.emit("daemon_state", &resp);
                            }
                        }
                    }
                    "quit" => {
                        // Tell daemon to shut down cleanly, then exit after grace period
                        post_daemon("/daemon/shutdown");
                        std::thread::spawn(move || {
                            std::thread::sleep(std::time::Duration::from_millis(500));
                            app.exit(0);
                        });
                    }
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            // All windows hide on close (never quit the process)
            if let WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .run(tauri::generate_context!())
        .expect("error running ZENO");
}
