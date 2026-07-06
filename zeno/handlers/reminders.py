import sqlite3
from typing import Any, Dict, Optional
from zeno.nlp.intent_schema import ParsedIntent

def handle_set_reminder(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """
    Handle 'set_reminder' intent.
    Inserts a new reminder.
    """
    slots = intent.slots
    message = slots.get("reminder_text", intent.raw_transcript)
    trigger_at = slots.get("trigger_time")
    
    query = """
        INSERT INTO reminders (title, message, trigger_at, status)
        VALUES (?, ?, ?, 'pending')
    """
    conn.execute(query, (message[:50], message, trigger_at))
    
    response = "Reminder set."
    if trigger_at:
        response += f" I'll notify you at {trigger_at}."
    return response

def handle_list_reminders(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """
    Handle 'list_reminders' intent.
    Lists pending reminders.
    """
    query = "SELECT message FROM reminders WHERE status = 'pending' LIMIT 5"
    cursor = conn.execute(query)
    results = cursor.fetchall()
    
    if not results:
        return "You have no upcoming reminders."
    
    messages = ", ".join([r['message'] for r in results])
    return f"Your reminders are: {messages}."
