import sqlite3
from zeno.nlp.intent_schema import ParsedIntent
from zeno.macros.engine import MacroEngine
from zeno.macros.safety import register_app

def _get_db_path(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    return row[2] if row else ":memory:"

def handle_setup_workspace(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """Intent: setup_workspace — slot: workspace_name"""
    name = intent.slots.get("workspace_name")
    if not name:
        return "Which workspace? Say 'set up coding' or 'list workspaces' to see options."
    engine = MacroEngine(db_path=_get_db_path(conn))
    return engine.run_workspace(str(name))

def handle_list_workspaces(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """Intent: list_workspaces — no slots needed"""
    engine = MacroEngine(db_path=_get_db_path(conn))
    names = engine.list_workspaces()
    if not names:
        return "No workspaces configured. Edit ~/Zeno/workspaces.yaml to add some."
    return "Available workspaces: " + ", ".join(names) + "."

def handle_stop_workspace(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """Intent: stop_workspace — cancels running macro"""
    # MacroEngine holds _cancel_event per-instance; daemon must pass its singleton engine.
    # Via dispatcher, we can't reach the running instance — acknowledge limitation.
    return "To stop a macro, I need to be running it from my main session. This will be fully wired in Phase 9."

def handle_register_workspace_app(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """Intent: register_workspace_app — slot: app_name"""
    app_name = intent.slots.get("app_name")
    if not app_name:
        return "Which app would you like to allow in macros?"
    db_path = _get_db_path(conn)
    try:
        register_app(str(app_name), db_path, is_work_app=True, user_override=True)
        return f"Done. '{app_name}' is now allowed in workspace macros."
    except Exception as e:
        return f"I couldn't register '{app_name}': {e}"
