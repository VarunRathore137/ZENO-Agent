import subprocess
import sys
import time
import webbrowser
from typing import Callable

try:
    import pygetwindow as gw
    _GW_AVAILABLE = True
except ImportError:
    _GW_AVAILABLE = False

try:
    import win32gui
    import win32con
    import win32api
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False

def execute_open_app(params: dict, **ctx) -> None:
    app_name = params["app_name"]
    args = params.get("args", [])
    try:
        subprocess.Popen([app_name] + args, shell=False)
    except FileNotFoundError:
        subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=False)
    
    wait_ms = params.get("wait_ms", 0)
    if wait_ms > 0:
        time.sleep(wait_ms / 1000.0)

def execute_open_url(params: dict, **ctx) -> None:
    url = params["url"]
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(f"URL must use http/https scheme: {url}")
    webbrowser.open(url)

def execute_focus_window(params: dict, **ctx) -> None:
    app_name = params["app_name"]
    if not _GW_AVAILABLE:
        print(f"[focus_window] pygetwindow not available, skipping", file=sys.stderr)
        return
    windows = gw.getWindowsWithTitle(app_name)
    if not windows:
        raise RuntimeError(f"No window found for '{app_name}'")
    windows[0].activate()

def execute_arrange_windows(params: dict, **ctx) -> None:
    layout = params.get("layout", "maximise_first")
    apps = params.get("apps", [])
    if layout != "maximise_first":
        print(f"[arrange_windows] Layout '{layout}' not supported in v1, skipping", file=sys.stderr)
        return
    if not apps or not _GW_AVAILABLE or not _WIN32_AVAILABLE:
        print("[arrange_windows] Conditions not met (empty apps or missing win32 deps), skipping", file=sys.stderr)
        return
    
    windows = gw.getWindowsWithTitle(apps[0])
    if windows:
        hwnd = windows[0]._hWnd
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    else:
        print(f"[arrange_windows] Window '{apps[0]}' not found, skipping", file=sys.stderr)
        return

def execute_toggle_dnd(params: dict, **ctx) -> None:
    enabled = params.get("enabled", True)
    try:
        value = "0" if enabled else "1"
        cmd = [
            "powershell", "-NonInteractive", "-NoProfile", "-Command",
            f"Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings' "
            f"-Name 'NOC_GLOBAL_SETTING_TOASTS_ENABLED' -Value {value} -ErrorAction SilentlyContinue"
        ]
        subprocess.run(cmd, shell=False, capture_output=True, timeout=5)
    except Exception as e:
        print(f"[toggle_dnd] Failed (non-fatal): {e}", file=sys.stderr)

def execute_announce(params: dict, **ctx) -> None:
    message = params["message"]
    tts_worker = ctx.get("tts_worker")
    if tts_worker is not None:
        tts_worker.enqueue(message)
    else:
        print(f"[Announce] {message}")

def execute_wait_ms(params: dict, **ctx) -> None:
    duration = params["duration"]
    time.sleep(min(int(duration), 30_000) / 1000.0)

STEP_EXECUTORS: dict[str, Callable] = {
    "open_app":        execute_open_app,
    "open_url":        execute_open_url,
    "focus_window":    execute_focus_window,
    "arrange_windows": execute_arrange_windows,
    "toggle_dnd":      execute_toggle_dnd,
    "announce":        execute_announce,
    "wait_ms":         execute_wait_ms,
}

def execute_step(step_type: str, params: dict, **ctx) -> None:
    executor = STEP_EXECUTORS.get(step_type)
    if not executor:
        raise ValueError(f"Unknown step type: {step_type}")
    executor(params, **ctx)
