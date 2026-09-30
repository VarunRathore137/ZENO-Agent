use std::sync::{Arc, Mutex};
use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::TrayIconBuilder,
    Emitter, Manager, WindowEvent,
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

/// Register ZENO in HKCU\...\Run so it starts with Windows.
#[cfg(windows)]
fn register_autostart(exe_path: &str) {
    use winreg::enums::*;
    use winreg::RegKey;
    let hkcu = RegKey::predef(HKEY_CURRENT_USER);
    let run_key = hkcu
        .open_subkey_with_flags(
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            KEY_SET_VALUE,
        )
        .expect("Failed to open Run registry key");
    run_key
        .set_value("ZENO", &exe_path)
        .expect("Failed to set ZENO autostart registry value");
    println!("[ZENO] Registered autostart: {}", exe_path);
}

#[cfg(not(windows))]
fn register_autostart(_exe_path: &str) {}

/// Check if the ZENO daemon is already running by probing its WebSocket port.
fn daemon_already_running() -> bool {
    // A successful TCP connect means someone is already listening on 8765.
    std::net::TcpStream::connect("127.0.0.1:8765").is_ok()
}

/// Spawn the Python ZENO daemon as a child subprocess.
/// Returns the child so the caller can kill it on exit.
/// Returns None (without spawning) if the daemon is already running.
fn spawn_daemon() -> Option<std::process::Child> {
    // If the Python daemon is already running (e.g. user started it manually
    // in a terminal), skip the spawn entirely.  Trying to bind the same port
    // again crashes the process silently because stdout/stderr are null.
    if daemon_already_running() {
        println!("[ZENO] Daemon already running on port 8765 — skipping spawn.");
        return None;
    }

    // Try miniconda first, then fall back to PATH python
    let python_candidates = [
        r"C:\Users\LENOVO\miniconda3\python.exe",
        r"C:\ProgramData\miniconda3\python.exe",
        "python",
    ];

    let project_dir = std::env::current_exe()
        .ok()
        .and_then(|p| {
            // Walk up from the .exe to find the project root (contains pyproject.toml)
            let mut dir = p.parent()?.to_path_buf();
            for _ in 0..6 {
                if dir.join("pyproject.toml").exists() {
                    return Some(dir);
                }
                dir = dir.parent()?.to_path_buf();
            }
            None
        })
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_default());

    for python in &python_candidates {
        let candidate = std::path::Path::new(python);
        // For PATH entries like "python", skip the exists() check
        let exists = candidate.is_absolute() && !candidate.exists();
        if exists {
            continue;
        }
        match std::process::Command::new(python)
            .args(["-m", "zeno"])
            .current_dir(&project_dir)
            // Detach stdout/stderr from Tauri's console
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
        {
            Ok(child) => {
                println!("[ZENO] Daemon started with PID {}", child.id());
                return Some(child);
            }
            Err(e) => {
                eprintln!("[ZENO] Failed to start daemon with '{}': {}", python, e);
            }
        }
    }

    eprintln!("[ZENO] WARNING: Could not start Python daemon. Make sure Python is on PATH.");
    None
}

/// Spawn a background tokio thread that connects to the Python daemon's
/// WebSocket on port 8765 and reacts to messages:
///   {"type": "overlay_show"} → show the overlay window
///   {"type": "overlay_hide"} → hide the overlay window
fn start_ws_listener(app_handle: tauri::AppHandle) {
    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("Failed to create tokio runtime");

        rt.block_on(async move {
            let url = "ws://127.0.0.1:8765";

            loop {
                tokio::time::sleep(std::time::Duration::from_secs(2)).await;

                match tokio_tungstenite::connect_async(url).await {
                    Err(e) => {
                        eprintln!("[ZENO WS] Connection to daemon failed: {e}. Retrying in 3s...");
                        tokio::time::sleep(std::time::Duration::from_secs(3)).await;
                        continue;
                    }
                    Ok((mut ws_stream, _)) => {
                        println!("[ZENO WS] Connected to daemon WebSocket on port 8765");
                        use futures_util::StreamExt;

                        while let Some(msg) = ws_stream.next().await {
                            match msg {
                                Ok(tokio_tungstenite::tungstenite::Message::Text(text)) => {
                                    if let Ok(json) =
                                        serde_json::from_str::<serde_json::Value>(&text)
                                    {
                                        match json.get("type").and_then(|v| v.as_str()) {
                                            Some("overlay_show") => {
                                                if let Some(win) =
                                                    app_handle.get_webview_window("overlay")
                                                {
                                                    let _ = win.show();
                                                    let _ = win.set_focus();
                                                }
                                            }
                                            Some("overlay_hide") => {
                                                if let Some(win) =
                                                    app_handle.get_webview_window("overlay")
                                                {
                                                    let _ = win.hide();
                                                }
                                            }
                                            _ => {}
                                        }
                                    }
                                }
                                Err(e) => {
                                    eprintln!("[ZENO WS] Stream error: {e}. Reconnecting...");
                                    break; // outer loop will reconnect
                                }
                                _ => {}
                            }
                        }
                        // Connection dropped — loop will reconnect
                    }
                }
            }
        });
    });
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Shared daemon child handle — wrapped in Arc<Mutex> so we can kill it
    // from the quit handler which runs in a different thread.
    let daemon_child: Arc<Mutex<Option<std::process::Child>>> = Arc::new(Mutex::new(None));
    let daemon_child_quit = daemon_child.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            commands::get_api_base,
            commands::show_overlay_window,
            commands::hide_overlay_window,
        ])
        .setup(move |app| {
            // ── 1. Register autostart in Windows Registry ──────────────────
            if let Ok(exe) = std::env::current_exe() {
                register_autostart(&exe.to_string_lossy());
            }

            // ── 2. Spawn Python ZENO daemon ────────────────────────────────
            {
                let child = spawn_daemon();
                if let Ok(mut lock) = daemon_child.lock() {
                    *lock = child;
                }
            }

            // ── 3. Wait a moment for daemon to bind its WebSocket, then connect ──
            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                std::thread::sleep(std::time::Duration::from_secs(3));
                start_ws_listener(app_handle);
            });

            // ── 4. Build system tray ───────────────────────────────────────
            let open_i  = MenuItemBuilder::with_id("open",  "Open Dashboard").build(app)?;
            let focus_i = MenuItemBuilder::with_id("focus", "Toggle Focus Mode").build(app)?;
            let mute_i  = MenuItemBuilder::with_id("mute",  "Mute Voice").build(app)?;
            let sep1    = tauri::menu::PredefinedMenuItem::separator(app)?;
            let quit_i  = MenuItemBuilder::with_id("quit",  "Quit ZENO").build(app)?;

            let menu = MenuBuilder::new(app)
                .items(&[&open_i, &focus_i, &mute_i, &sep1, &quit_i])
                .build()?;

            TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .tooltip("ZENO — Your Personal AI Assistant")
                .show_menu_on_left_click(false)
                .on_tray_icon_event(|tray, event| {
                    // Left click: ALWAYS show and focus the dashboard.
                    // Do NOT toggle hide — the race between App.tsx's show()
                    // useEffect and this handler causes is_visible() to return
                    // true prematurely, hiding the window immediately on first
                    // click and requiring 5-6 clicks to land on 'show'.
                    // Close button (CloseRequested) hides to tray instead.
                    if let tauri::tray::TrayIconEvent::Click {
                        button: tauri::tray::MouseButton::Left,
                        button_state: tauri::tray::MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(win) = app.get_webview_window("main") {
                            let _ = win.unminimize();
                            let _ = win.show();
                            let _ = win.set_focus();
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
                            if let Some(win) = app.get_webview_window("main") {
                                let _ = win.emit("daemon_state", &resp);
                            }
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
                        // 1. Tell Python daemon to shut down via HTTP
                        post_daemon("/daemon/shutdown");
                        // 2. Kill the child process just in case
                        if let Ok(mut lock) = daemon_child_quit.lock() {
                            if let Some(child) = lock.as_mut() {
                                let _ = child.kill();
                            }
                        }
                        // 3. Exit Tauri after short grace period
                        let app_handle = app.clone();
                        std::thread::spawn(move || {
                            std::thread::sleep(std::time::Duration::from_millis(600));
                            app_handle.exit(0);
                        });
                    }
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            // All windows hide on close — never actually quit
            if let WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .run(tauri::generate_context!())
        .expect("error running ZENO");
}
