import pytest
import sqlite3
import os
from pathlib import Path
from zeno.nlp.intent_schema import ParsedIntent
from zeno.dispatcher.router import dispatch
from zeno.db import get_connection

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_zeno.db"
    schema_file = Path(__file__).parent.parent.parent / "zeno_schema.sql"
    
    conn = get_connection(db_file)
    with open(schema_file, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.close()
    
    return db_file

def test_dispatch_add_task(test_db):
    intent = ParsedIntent(
        intent_category="task_management",
        intent_name="add_task",
        slots={"title": "Test Task", "priority": "high"},
        raw_transcript="add a high priority task called Test Task"
    )
    
    response = dispatch(intent, db_path=test_db)
    assert "Task added: Test Task" in response
    
    # Verify DB state
    conn = get_connection(test_db)
    cursor = conn.execute("SELECT title, priority FROM tasks WHERE title = 'Test Task'")
    row = cursor.fetchone()
    assert row is not None
    assert row['title'] == "Test Task"
    assert row['priority'] == "high"
    conn.close()

def test_dispatch_capture_idea(test_db):
    intent = ParsedIntent(
        intent_category="notes",
        intent_name="capture_idea",
        slots={"note_text": "A brilliant idea"},
        raw_transcript="capture an idea a brilliant idea"
    )
    
    response = dispatch(intent, db_path=test_db)
    assert "Idea captured" in response
    
    # Verify DB state
    conn = get_connection(test_db)
    cursor = conn.execute("SELECT content FROM notes WHERE note_type = 'idea'")
    row = cursor.fetchone()
    assert row is not None
    assert row['content'] == "A brilliant idea"
    conn.close()

def test_dispatch_unknown_intent(test_db):
    intent = ParsedIntent(
        intent_category="unknown",
        intent_name="dance_jig",
        slots={},
        raw_transcript="dance a jig"
    )
    
    response = dispatch(intent, db_path=test_db)
    assert "I don't have a handler for that yet" in response
