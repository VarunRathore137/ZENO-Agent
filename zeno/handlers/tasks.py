import sqlite3
from typing import Any, Dict, Optional
from zeno.nlp.intent_schema import ParsedIntent

def handle_add_task(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """
    Handle 'add_task' intent.
    Inserts a new task into the database.
    """
    slots = intent.slots
    title = slots.get("title", "New Task")
    priority = slots.get("priority", "medium")
    due_date = slots.get("due_date")
    estimated_minutes = slots.get("estimated_minutes")
    
    query = """
        INSERT INTO tasks (title, priority, due_date, estimated_minutes, source)
        VALUES (?, ?, ?, ?, 'voice')
    """
    conn.execute(query, (title, priority, due_date, estimated_minutes))
    
    response = f"Task added: {title}"
    if due_date:
        response += f" due {due_date}"
    return response

def handle_complete_task(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """
    Handle 'complete_task' intent.
    Marks a task as completed.
    """
    # In a real implementation, we'd fuzzy match the task_ref slot to an ID
    # For now, we'll assume a title match or similar logic
    task_ref = intent.slots.get("task_ref")
    if not task_ref:
        return "I'm sorry, which task should I mark as complete?"
    
    query = "UPDATE tasks SET status = 'completed', completed_at = datetime('now') WHERE title LIKE ?"
    cursor = conn.execute(query, (f"%{task_ref}%",))
    
    if cursor.rowcount > 0:
        return f"Marked '{task_ref}' as complete."
    else:
        return f"I couldn't find a task matching '{task_ref}'."

def handle_query_tasks(intent: ParsedIntent, conn: sqlite3.Connection) -> str:
    """
    Handle 'query_tasks' intent.
    Lists pending tasks.
    """
    query = "SELECT title FROM v_todays_tasks LIMIT 5"
    cursor = conn.execute(query)
    tasks = cursor.fetchall()
    
    if not tasks:
        return "You have no pending tasks for today."
    
    task_list = ", ".join([t['title'] for t in tasks])
    return f"Your tasks for today are: {task_list}."
