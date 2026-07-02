import sqlite3
from typing import Any, Dict, Optional
from zeno.nlp.intent_schema import ParsedIntent
from zeno.ai.rubber_duck import (
    RubberDuckSession,
    load_latest_session,
    save_session,
)

def handle_start_new_session(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """
    Handle 'start_new_session' intent.
    """
    query = """
        INSERT INTO sessions (session_date, started_at)
        VALUES (date('now'), datetime('now'))
    """
    conn.execute(query)
    return "New session started. Welcome back."

def handle_initiate_shutdown(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """
    Handle 'initiate_shutdown' intent.
    """
    # Mark most recent session as ended
    query = """
        UPDATE sessions 
        SET ended_at = datetime('now') 
        WHERE id = (SELECT max(id) FROM sessions)
    """
    conn.execute(query)
    return "Initiating shutdown. Good work today."


def handle_start_rubber_duck(intent: ParsedIntent, conn: sqlite3.Connection) -> dict:
    """
    Handle 'start_rubber_duck' intent.

    Returns a dict with:
      - 'session': the RubberDuckSession (new or resumed)
      - 'response': text to speak to the user
    """
    project_slug: str = intent.slots.get("project_slug", "untitled")

    # Try to resume an existing in-progress session
    session = load_latest_session(project_slug, conn)
    if session is not None:
        response = (
            f"Welcome back. Resuming Rubber Duck session for '{project_slug}'. "
            f"We were on the {session.state.replace('_', ' ').title()} phase."
        )
    else:
        # Start a fresh session
        session = RubberDuckSession(project_slug=project_slug)
        session = save_session(session, conn)
        response = (
            f"Starting Rubber Duck mode for '{project_slug}'. "
            "Let's work through your problem step by step. "
            "First, tell me: what problem are you trying to solve?"
        )

    conn.commit()
    return {"session": session, "response": response}
