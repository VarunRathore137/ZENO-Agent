"""
zeno/dispatcher/router.py
─────────────────────────
Routes parsed intents to their handlers.

Two routing paths:
  1. STRUCTURED DB INTENTS → local handler functions (tasks, notes, etc.)
  2. OS AGENT INTENTS → HTTP POST to ZENO OS Agent on port 8765

Intent → tool name mapping for OS agent intents:
  Voice command "open chrome" → intent "open_app" → agent tool "openApplication"
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from typing import Dict, Callable, Any

from zeno.nlp.intent_schema import ParsedIntent
from zeno.db import db_session
from zeno.handlers import tasks, notes, reminders, sessions, workspaces

log = logging.getLogger("zeno.dispatcher")

# ---------------------------------------------------------------------------
# Path 1: Local handlers (DB-backed structured intents)
# ---------------------------------------------------------------------------
HANDLER_MAP: Dict[str, Callable[[ParsedIntent, sqlite3.Connection], str]] = {
    # Tasks
    "add_task": tasks.handle_add_task,
    "complete_task": tasks.handle_complete_task,
    "query_tasks": tasks.handle_query_tasks,

    # Notes
    "capture_idea": notes.handle_capture_idea,
    "search_notes": notes.handle_search_notes,

    # Reminders
    "set_reminder": reminders.handle_set_reminder,
    "list_reminders": reminders.handle_list_reminders,

    # Sessions
    "start_new_session": sessions.handle_start_new_session,
    "initiate_shutdown": sessions.handle_initiate_shutdown,

    # Workspaces
    "setup_workspace":          workspaces.handle_setup_workspace,
    "list_workspaces":          workspaces.handle_list_workspaces,
    "stop_workspace":           workspaces.handle_stop_workspace,
    "register_workspace_app":   workspaces.handle_register_workspace_app,
}

# ---------------------------------------------------------------------------
# Path 2: OS agent intents → tool name + args extractor
# Maps intent_name → (agent_tool_name, args_builder_fn)
# ---------------------------------------------------------------------------
def _slots(intent: ParsedIntent) -> Dict[str, Any]:
    return intent.slots or {}


OS_AGENT_INTENT_MAP: Dict[str, tuple[str, Callable[[ParsedIntent], Dict[str, Any]]]] = {
    # Applications
    "open_app":         ("openApplication",   lambda i: {"name": i.slots.get("app_name", "")}),
    "close_app":        ("closeApplication",  lambda i: {"name": i.slots.get("app_name", "")}),

    # Websites & search
    "open_website":     ("openWebsite",       lambda i: {"name": i.slots.get("site_name", i.slots.get("url", ""))}),
    "search_web":       ("searchWeb",         lambda i: {"query": i.slots.get("query", i.raw_transcript)}),
    "search_youtube":   ("searchYouTube",     lambda i: {"query": i.slots.get("query", i.raw_transcript)}),
    "search_google":    ("searchGoogle",      lambda i: {"query": i.slots.get("query", i.raw_transcript)}),

    # Files
    "create_file":      ("createFile",        lambda i: {"filename": i.slots.get("filename", ""), "content": i.slots.get("content", "")}),
    "read_file":        ("readFile",          lambda i: {"filename": i.slots.get("filename", "")}),
    "delete_file":      ("deleteFile",        lambda i: {"filename": i.slots.get("filename", "")}),
    "list_files":       ("listFiles",         lambda i: {"directory": i.slots.get("directory", "~")}),
    "search_files":     ("searchFiles",       lambda i: {"query": i.slots.get("query", "")}),

    # System & PC
    "set_volume":       ("setVolume",         lambda i: {"level": i.slots.get("level", 50)}),
    "volume_up":        ("volumeUp",          lambda i: {}),
    "volume_down":      ("volumeDown",        lambda i: {}),
    "mute_toggle":      ("muteToggle",        lambda i: {}),
    "get_system_info":  ("systemInfo",        lambda i: {}),
    "get_gpu_info":     ("gpuInfo",           lambda i: {}),

    # Screen vision
    "take_screenshot":  ("takeScreenshot",    lambda i: {}),
    "read_screen":      ("readScreen",        lambda i: {}),

    # Clipboard
    "get_clipboard":    ("getClipboard",      lambda i: {}),
    "paste_clipboard":  ("pasteClipboard",    lambda i: {}),

    # Weather & news
    "get_weather":      ("getWeather",        lambda i: {"location": i.slots.get("location", "")}),
    "get_news":         ("getNews",           lambda i: {"category": i.slots.get("category", "general")}),

    # Terminal
    "run_terminal":     ("runTerminalCommand", lambda i: {"command": i.slots.get("command", "")}),

    # Window management
    "minimize_window":  ("minimizeWindow",    lambda i: {"title": i.slots.get("title", "")}),
    "maximize_window":  ("maximizeWindow",    lambda i: {"title": i.slots.get("title", "")}),
    "close_window":     ("closeWindow",       lambda i: {"title": i.slots.get("title", "")}),

    # Google Suite
    "check_calendar":   ("getCalendarEvents", lambda i: {"days": i.slots.get("days", 7)}),
    "add_calendar_event": ("createCalendarEvent", lambda i: _slots(i)),
    "send_email":       ("sendEmail",         lambda i: _slots(i)),
    "check_email":      ("getEmails",         lambda i: {}),

    # Coding
    "create_python_file": ("createPythonFile", lambda i: {"filename": i.slots.get("filename", ""), "content": i.slots.get("content", "")}),
    "run_python":       ("runPythonScript",   lambda i: {"filename": i.slots.get("filename", "")}),
}

# Full set of intent names that route to the OS agent
OS_AGENT_INTENTS = set(OS_AGENT_INTENT_MAP.keys())


# ---------------------------------------------------------------------------
# Main dispatch function
# ---------------------------------------------------------------------------
def dispatch(intent: ParsedIntent, db_path: str | None = None) -> str:
    """
    Route a parsed intent to the correct handler.
    Returns a human-readable response string for TTS.
    """
    intent_name = intent.intent_name

    # Path 2: OS agent intent
    if intent_name in OS_AGENT_INTENTS:
        return _dispatch_to_agent(intent)

    # Path 1: Local DB-backed handler
    handler = HANDLER_MAP.get(intent_name)
    if not handler:
        return (
            f"I understand you want to '{intent_name}', "
            f"but I don't have a handler for that yet."
        )

    try:
        with db_session(db_path=db_path) as conn:
            return handler(intent, conn)
    except Exception as e:
        log.error("Handler error for intent '%s': %s", intent_name, e, exc_info=True)
        return "I'm sorry, I encountered an error while processing that command."


def _dispatch_to_agent(intent: ParsedIntent) -> str:
    """Route an OS-agent intent to the ZENO OS Agent via HTTP."""
    from zeno.agent.dispatch import dispatch_to_agent, is_agent_available

    tool_name, args_fn = OS_AGENT_INTENT_MAP[intent.intent_name]
    args = args_fn(intent)

    if not is_agent_available():
        log.warning("OS Agent unavailable — cannot dispatch '%s'", tool_name)
        return (
            "The OS Agent is not running. "
            "Please start it with 'python -m zeno.agent.server'."
        )

    try:
        result = dispatch_to_agent(tool_name, args)
        # Try to get a human-readable result string
        if isinstance(result, dict):
            return result.get("result") or result.get("output") or f"Done: {tool_name}"
        return str(result) or f"Done: {tool_name}"
    except RuntimeError as e:
        log.error("Agent dispatch error: %s", e)
        return f"I ran into an issue: {e}"
