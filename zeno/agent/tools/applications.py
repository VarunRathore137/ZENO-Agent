"""
Application control: launch and close common applications.

Uses the OS backend for platform-independent app launching and closing.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict

from ..registry import ToolError, register
from ..backends import get_backend

APP_COMMANDS: Dict[str, Dict[str, str]] = {
    "notepad":        {"exe": "notepad.exe",     "image": "notepad.exe",          "label": "Notepad",            "linux_cmd": "gedit",                    "linux_image": "gedit"},
    "chrome":         {"exe": "chrome.exe",       "image": "chrome.exe",           "label": "Google Chrome",      "linux_cmd": "google-chrome-stable",     "linux_image": "chrome"},
    "edge":           {"exe": "msedge.exe",       "image": "msedge.exe",           "label": "Microsoft Edge",     "linux_cmd": "microsoft-edge-stable",    "linux_image": "msedge"},
    "vscode":         {"exe": "code.cmd",         "image": "Code.exe",             "label": "Visual Studio Code", "linux_cmd": "code",                     "linux_image": "code"},
    "calculator":     {"shell": "calc",           "image": "CalculatorApp.exe",    "label": "Calculator",         "linux_cmd": "gnome-calculator",         "linux_image": "gnome-calculator"},
    "calc":           {"shell": "calc",           "image": "CalculatorApp.exe",    "label": "Calculator",         "linux_cmd": "gnome-calculator",         "linux_image": "gnome-calculator"},
    "file explorer":  {"shell": "explorer",       "image": "explorer.exe",         "label": "File Explorer",      "linux_cmd": "nautilus",                 "linux_image": "nautilus"},
    "explorer":       {"shell": "explorer",       "image": "explorer.exe",         "label": "File Explorer",      "linux_cmd": "nautilus",                 "linux_image": "nautilus"},
    "task manager":   {"shell": "taskmgr",        "image": "Taskmgr.exe",          "label": "Task Manager",       "linux_cmd": "gnome-system-monitor",     "linux_image": "gnome-system-monitor"},
    "taskmanager":    {"shell": "taskmgr",        "image": "Taskmgr.exe",          "label": "Task Manager",       "linux_cmd": "gnome-system-monitor",     "linux_image": "gnome-system-monitor"},
    "settings":       {"uwp": "ms-settings:",     "image": "SystemSettings.exe",   "label": "Settings",           "linux_cmd": "gnome-control-center",     "linux_image": "gnome-control-center"},
    "command prompt": {"exe": "cmd.exe",          "image": "cmd.exe",              "label": "Command Prompt",     "linux_cmd": "gnome-terminal",           "linux_image": "gnome-terminal-server"},
    "cmd":            {"exe": "cmd.exe",          "image": "cmd.exe",              "label": "Command Prompt",     "linux_cmd": "gnome-terminal",           "linux_image": "gnome-terminal-server"},
    "powershell":     {"exe": "powershell.exe",   "image": "powershell.exe",       "label": "PowerShell",         "linux_cmd": "pwsh",                     "linux_image": "pwsh"},
    "wordpad":        {"shell": "write",           "image": "wordpad.exe",          "label": "WordPad",            "linux_cmd": "abiword",                  "linux_image": "abiword"},
    "paint":          {"shell": "mspaint",         "image": "mspaint.exe",          "label": "Paint",              "linux_cmd": "gimp",                     "linux_image": "gimp"},
    "snipping tool":  {"uwp": "ms-screenclip:",   "image": "ScreenClippingHost.exe","label": "Snipping Tool",     "linux_cmd": "gnome-screenshot",         "linux_image": "gnome-screenshot"},
    # Common third-party apps — resolved dynamically via _find_app_exe()
    "spotify":        {"exe": "Spotify.exe",      "image": "Spotify.exe",          "label": "Spotify",            "linux_cmd": "spotify",                  "linux_image": "spotify"},
    "discord":        {"exe": "Discord.exe",      "image": "Discord.exe",          "label": "Discord",            "linux_cmd": "discord",                  "linux_image": "discord"},
    "steam":          {"exe": "steam.exe",        "image": "steam.exe",            "label": "Steam",              "linux_cmd": "steam",                    "linux_image": "steam"},
    "obs":            {"exe": "obs64.exe",        "image": "obs64.exe",            "label": "OBS Studio",         "linux_cmd": "obs",                      "linux_image": "obs"},
    "vlc":            {"exe": "vlc.exe",          "image": "vlc.exe",              "label": "VLC",                "linux_cmd": "vlc",                      "linux_image": "vlc"},
    "zoom":           {"exe": "Zoom.exe",         "image": "Zoom.exe",             "label": "Zoom",               "linux_cmd": "zoom",                     "linux_image": "zoom"},
    "slack":          {"exe": "slack.exe",        "image": "slack.exe",            "label": "Slack",              "linux_cmd": "slack",                    "linux_image": "slack"},
    "notion":         {"uwp": "notion:",          "image": "Notion.exe",           "label": "Notion",             "linux_cmd": "notion-app",               "linux_image": "notion"},
    "terminal":       {"exe": "wt.exe",           "image": "WindowsTerminal.exe",  "label": "Windows Terminal",   "linux_cmd": "gnome-terminal",           "linux_image": "gnome-terminal-server"},
    "windows terminal": {"exe": "wt.exe",         "image": "WindowsTerminal.exe",  "label": "Windows Terminal",   "linux_cmd": "gnome-terminal",           "linux_image": "gnome-terminal-server"},
}


# Candidate install paths searched when the exe is not on PATH.
# Ordered: LocalAppData first (user installs), then Program Files.
_SEARCH_ROOTS = [
    os.path.expandvars(r"%LOCALAPPDATA%"),
    os.path.expandvars(r"%APPDATA%"),
    os.path.expandvars(r"%PROGRAMFILES%"),
    os.path.expandvars(r"%PROGRAMFILES(X86)%"),
]

# Well-known sub-paths for apps that never land on PATH
_KNOWN_PATHS: Dict[str, list] = {
    "Spotify.exe": [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
    ],
    "chrome.exe": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ],
    "msedge.exe": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "Discord.exe": [
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\app-*\Discord.exe"),  # glob
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\Discord.exe"),
    ],
    "steam.exe": [
        r"C:\Program Files (x86)\Steam\steam.exe",
        r"C:\Program Files\Steam\steam.exe",
    ],
    "obs64.exe": [
        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
    ],
    "vlc.exe": [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ],
    "Zoom.exe": [
        os.path.expandvars(r"%APPDATA%\Zoom\bin\Zoom.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Zoom\Zoom.exe"),
    ],
}


def _find_app_exe(exe_name: str) -> str:
    """
    Return the full path to an exe, or just the exe name if found on PATH.
    Checks PATH first, then _KNOWN_PATHS, then does a shallow directory scan.
    """
    import glob

    # 1. Already on PATH?
    if shutil.which(exe_name):
        return exe_name

    # 2. Check known install paths (including globs for versioned dirs)
    for pattern in _KNOWN_PATHS.get(exe_name, []):
        matches = glob.glob(pattern)
        if matches:
            return matches[0]  # take first glob match (most recent version)

    # 3. Shallow scan of common roots — one level deep to keep it fast
    for root in _SEARCH_ROOTS:
        if not os.path.isdir(root):
            continue
        for entry in os.scandir(root):
            candidate = os.path.join(entry.path, exe_name)
            if os.path.isfile(candidate):
                return candidate

    # 4. Give up — return bare name and let Windows shell resolve it
    return exe_name




def _resolve_app(key: str) -> Dict[str, str]:
    norm = (key or "").strip().lower()
    if norm in APP_COMMANDS:
        return APP_COMMANDS[norm]
    # Allow loose aliases
    aliases = {
        "code":               "vscode",
        "visual studio code": "vscode",
        "vs code":            "vscode",
        "google chrome":      "chrome",
        "microsoft edge":     "edge",
        "calc":               "calculator",
        "settings app":       "settings",
        "file explorer":      "file explorer",
        "windows explorer":   "file explorer",
        "windows terminal":   "terminal",
        "wt":                 "terminal",
        "obs studio":         "obs",
        "video lan":          "vlc",
    }
    if norm in aliases and aliases[norm] in APP_COMMANDS:
        return APP_COMMANDS[aliases[norm]]
    raise ToolError(
        f"Unrecognized application '{key}'. Supported: "
        f"{', '.join(sorted({v['label'] for v in APP_COMMANDS.values()}))}."
    )


def _is_hyprland() -> bool:
    return os.environ.get("XDG_CURRENT_DESKTOP", "").lower() == "hyprland"


def _launch_hyprland(cmd: str, floating: bool, size: str = "60% 60%") -> None:
    prefix = f"[float size {size} center]" if floating else ""
    subprocess.Popen(
        f"hyprctl dispatch exec -- {prefix} {cmd}",
        shell=True,
        close_fds=True,
        start_new_session=True,
    )


@register("openApplication")
def open_application(args: Dict[str, Any]) -> Dict[str, Any]:
    name = args.get("name") or args.get("application")
    if not name:
        raise ToolError("Parameter 'name' (application name) is required.")
    spec = _resolve_app(str(name))
    floating = bool(args.get("floating", False))
    size = args.get("size", "60% 60%")
    linux_cmd = spec.get("linux_cmd")
    if floating and _is_hyprland() and linux_cmd:
        _launch_hyprland(linux_cmd, floating=True, size=size)
    else:
        # For exe-based apps: resolve the full path dynamically so apps like
        # Spotify and Chrome that live in AppData / Program Files (not on PATH)
        # are found correctly on Windows.
        if "exe" in spec and os.name == "nt":
            resolved = _find_app_exe(spec["exe"])
            resolved_spec = dict(spec, exe=resolved)
            get_backend().launcher.launch(resolved_spec)
        else:
            get_backend().launcher.launch(spec)
    return {"result": f"{spec['label']} opened."}


@register("closeApplication")
def close_application(args: Dict[str, Any]) -> Dict[str, Any]:
    name = args.get("name") or args.get("application")
    force = bool(args.get("force", False))
    if not name:
        raise ToolError("Parameter 'name' (application name) is required.")
    spec = _resolve_app(str(name))
    get_backend().launcher.close(spec, force)
    return {"result": f"Closed {spec['label']}."}


__all__ = ["open_application", "close_application", "APP_COMMANDS"]
