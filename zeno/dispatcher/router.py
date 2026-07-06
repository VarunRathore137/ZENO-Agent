import sqlite3
import sys
from typing import Dict, Callable

from zeno.nlp.intent_schema import ParsedIntent
from zeno.db import db_session
from zeno.handlers import tasks, notes, reminders, sessions

# Mapping of intent_name -> handler_function
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
}

def dispatch(intent: ParsedIntent, db_path: str | None = None) -> str:
    """
    Main entry point for dispatching a parsed intent to its handler.
    Opens a database session and executes the corresponding handler.
    """
    handler = HANDLER_MAP.get(intent.intent_name)
    
    if not handler:
        return f"I understand you want to '{intent.intent_name}', but I don't have a handler for that yet."
        
    try:
        with db_session(db_path=db_path) as conn:
            response = handler(intent, conn)
            return response
    except Exception as e:
        print(f"Error dispatching intent '{intent.intent_name}': {e}", file=sys.stderr)
        return "I'm sorry, I encountered an error while trying to process that command."
