import sqlite3
from typing import Any, Dict, Optional
from zeno.nlp.intent_schema import ParsedIntent

def handle_capture_idea(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """
    Handle 'capture_idea' intent.
    Inserts a new idea note.
    """
    note_text = intent.slots.get("note_text", intent.raw_transcript)
    
    query = """
        INSERT INTO notes (content, note_type, source)
        VALUES (?, 'idea', 'voice')
    """
    conn.execute(query, (note_text,))
    
    return f"Idea captured: {note_text[:50]}..."

def handle_search_notes(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """
    Handle 'search_notes' intent.
    Performs FTS5 search.
    """
    query_text = intent.slots.get("search_query")
    if not query_text:
        return "What would you like me to search for?"
    
    # Using FTS5 virtual table
    query = """
        SELECT title, content FROM notes_fts 
        WHERE notes_fts MATCH ? 
        LIMIT 3
    """
    cursor = conn.execute(query, (query_text,))
    results = cursor.fetchall()
    
    if not results:
        return f"I couldn't find any notes about '{query_text}'."
    
    titles = ", ".join([r['title'] or r['content'][:20] for r in results])
    return f"Found some notes: {titles}."
