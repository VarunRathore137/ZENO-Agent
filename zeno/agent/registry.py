"""
ZENO Desktop Control Agent — Central tool registry.

Each tool module registers handlers into a flat dict `TOOLS` mapping
tool_name -> callable(args: dict) -> dict.

Handlers return a plain dict, typically {"result": "<status string>"}.
Errors should raise ToolError(message) so server.py can map them to {error}.
Shared singletons (Playwright browser/page, confirmation store, etc.) live
on the `State` object so handlers stay stateless and easy to test.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict


class ToolError(Exception):
    """Raised by a tool handler to signal a clean, user-facing failure."""

    def __init__(self, message: str, *, fatal: bool = False):
        super().__init__(message)
        self.message = message
        self.fatal = fatal


class State:
    """Process-wide shared state for tool handlers."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        # Confirmation tokens for dangerous (power) actions.
        # token -> {"action": <tool_name>, "expires": <epoch>}
        self.confirmations: Dict[str, Dict[str, Any]] = {}
        # Playwright singletons — lazily initialized on first browser tool use.
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        # Sudo command store: command_id -> { command, expires_at }
        self.sudo_commands: Dict[str, Dict[str, Any]] = {}

    def reset_playwright(self) -> None:
        """Tear down any cached Playwright resources (used on errors)."""
        try:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
        except Exception:
            pass


STATE = State()

# tool_name -> handler(args: dict) -> dict
TOOLS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


def register(name: str):
    """Decorator to register a handler under a tool name."""

    def deco(fn: Callable[[Dict[str, Any]], Dict[str, Any]]):
        TOOLS[name] = fn
        return fn

    return deco


# The set of all tool names ZENO may route to this agent.
DESKTOP_TOOL_NAMES = [
    "openApplication", "closeApplication",
    "openWebsite", "searchWeb", "searchYouTube", "searchGoogle", "searchGitHub",
    "createFile", "readFile", "renameFile", "deleteFile", "moveFile",
    "openFolder", "listFiles", "searchFiles",
    "volumeUp", "volumeDown", "muteToggle", "setVolume",
    "requestPowerAction", "executePowerAction",
    "minimizeWindow", "maximizeWindow", "closeWindow", "switchApplication",
    "copySelected", "pasteClipboard", "getClipboard", "clearClipboard",
    "takeScreenshot", "saveScreenshot", "analyzeScreenshot", "readScreen",
    "desktopBrowserOpen", "desktopBrowserNavigate", "desktopBrowserOpenTab",
    "desktopBrowserCloseTab", "desktopBrowserSearch",
    "desktopBrowserOpenYoutubeVideo", "desktopBrowserClick",
    "desktopBrowserType", "desktopBrowserFillForm", "desktopBrowserGoBack",
    "desktopBrowserGoForward", "desktopBrowserScroll", "desktopBrowserReadText",
    "desktopBrowserGetLinks", "desktopBrowserSetMode",
    "browserMediaControl", "browserTabAction",
    "createPythonFile", "runPythonScript", "createProjectFolder", "writeCodeFile",
    "systemInfo", "gpuInfo", "temperatureInfo",
    "brightnessUp", "brightnessDown", "setBrightness",
    "enableAutoStart", "disableAutoStart", "getAutoStartStatus",
    "requestTerminalAction", "runTerminalCommand",
    "provideSudoPassword", "installPackage", "isCommandAllowed",
    "iitmQuickLinks", "iitmOpen", "iitmOpenCustom",
    "shutdownZeno",
    "getWeather",
    "osType", "osPress", "osClick",
    "switchWorkspace", "listWorkspaces", "moveToWorkspace",
    "getNews",
    "exportConversation", "listExports",
    "getCalendarEvents", "createCalendarEvent",
    "sendEmail", "getEmails", "getTasks", "createTask",
    "cameraList", "cameraOn", "cameraOff",
]


def load_all() -> None:
    """Eagerly import all tool modules so their @register decorators run."""
    import zeno.agent.tools.confirmation
    import zeno.agent.tools.applications
    import zeno.agent.tools.websites
    import zeno.agent.tools.search
    import zeno.agent.tools.files
    import zeno.agent.tools.pc
    import zeno.agent.tools.windows
    import zeno.agent.tools.clipboard
    import zeno.agent.tools.screenshot
    import zeno.agent.tools.browser
    import zeno.agent.tools.coding
    import zeno.agent.tools.system
    import zeno.agent.tools.startup
    import zeno.agent.tools.terminal
    import zeno.agent.tools.iitm
    import zeno.agent.tools.weather
    import zeno.agent.tools.hyprland
    import zeno.agent.tools.news
    import zeno.agent.tools.conversation
    import zeno.agent.tools.os_input
    import zeno.agent.tools.google
    import zeno.agent.tools.camera


__all__ = ["TOOLS", "STATE", "DESKTOP_TOOL_NAMES", "ToolError", "register", "load_all"]
