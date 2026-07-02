"""
zeno/ai/briefing.py — Morning briefing context builder and LLM synthesis.

Design (from DECISIONS.md):
  - Context is gathered from 5 specific DB/file sources (total < 800 tokens).
  - LLM synthesises into a conversational briefing under 120 spoken words.
  - Connect to: `deliver_briefing` intent or daemon startup sequence.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from zeno.ai.prompts import load_prompt

if TYPE_CHECKING:
    from zeno.ai.providers import ProviderRouter


# ---------------------------------------------------------------------------
# Context gathering
# ---------------------------------------------------------------------------

def _gather_pending_tasks(conn: sqlite3.Connection) -> str:
    """
    Fetch up to 10 pending tasks from v_morning_brief_tasks view.
    Returns a compact text block.
    """
    try:
        rows = conn.execute(
            """
            SELECT title, priority, due_date, status
            FROM v_morning_brief_tasks
            ORDER BY
                CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                due_date ASC NULLS LAST
            LIMIT 10
            """
        ).fetchall()
    except sqlite3.OperationalError:
        # View doesn't exist yet (DB not initialised)
        return ""

    if not rows:
        return "No pending tasks today."

    lines = ["Pending tasks:"]
    for row in rows:
        due = f" (due {row['due_date']})" if row["due_date"] else ""
        lines.append(f"  [{row['priority'].upper()}] {row['title']}{due}")
    return "\n".join(lines)


def _gather_last_session(conn: sqlite3.Connection) -> str:
    """
    Fetch the most recent session's departure context.
    Returns a compact text block.
    """
    try:
        row = conn.execute(
            """
            SELECT last_active_task, pending_items, user_notes, energy_level
            FROM sessions
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
    except sqlite3.OperationalError:
        return ""

    if row is None:
        return "No previous session recorded."

    parts: list[str] = ["Last session:"]
    if row["last_active_task"]:
        parts.append(f"  Last task: {row['last_active_task']}")
    if row["pending_items"]:
        parts.append(f"  Pending: {row['pending_items']}")
    if row["energy_level"]:
        parts.append(f"  Energy level: {row['energy_level']}")
    if row["user_notes"]:
        parts.append(f"  Notes: {row['user_notes']}")
    return "\n".join(parts)


def _gather_calendar_events(conn: sqlite3.Connection) -> str:
    """
    Fetch today's time blocks (used as calendar events).
    Returns a compact text block.
    """
    today = date.today().isoformat()
    try:
        rows = conn.execute(
            """
            SELECT title, start_time, end_time
            FROM time_blocks
            WHERE date = ?
            ORDER BY start_time ASC
            LIMIT 8
            """,
            (today,),
        ).fetchall()
    except sqlite3.OperationalError:
        return ""

    if not rows:
        return "No calendar events today."

    lines = ["Today's schedule:"]
    for row in rows:
        lines.append(f"  {row['start_time']}–{row['end_time']}: {row['title']}")
    return "\n".join(lines)


def _gather_focus_window(conn: sqlite3.Connection) -> str:
    """Fetch peak_focus_window from behaviour_patterns for scheduling advice."""
    try:
        row = conn.execute(
            "SELECT peak_focus_window FROM behaviour_patterns LIMIT 1"
        ).fetchone()
    except sqlite3.OperationalError:
        return ""

    if row and row["peak_focus_window"]:
        return f"Your peak focus window: {row['peak_focus_window']}"
    return ""


def _gather_weekly_summary(conn: sqlite3.Connection) -> str:
    """Fetch the latest weekly analytics summary."""
    try:
        row = conn.execute(
            """
            SELECT week_start, deep_work_hours, tasks_completed, insight_summary
            FROM analytics_weekly
            ORDER BY week_start DESC LIMIT 1
            """
        ).fetchone()
    except sqlite3.OperationalError:
        return ""

    if row is None:
        return ""

    parts: list[str] = [f"This week (since {row['week_start']}):"]
    if row["deep_work_hours"] is not None:
        parts.append(f"  Deep work: {row['deep_work_hours']:.1f} hrs")
    if row["tasks_completed"] is not None:
        parts.append(f"  Tasks completed: {row['tasks_completed']}")
    if row["insight_summary"]:
        # Truncate to one sentence to keep tokens low
        summary = row["insight_summary"].split(".")[0].strip()
        if summary:
            parts.append(f"  Insight: {summary}.")
    return "\n".join(parts)


def build_briefing_context(conn: sqlite3.Connection) -> str:
    """
    Assemble all context sources into a single compact string for the LLM.
    Targets < 800 tokens total.
    """
    sections: list[str] = [
        f"Date: {date.today().strftime('%A, %d %B %Y')}",
        _gather_last_session(conn),
        _gather_pending_tasks(conn),
        _gather_calendar_events(conn),
        _gather_focus_window(conn),
        _gather_weekly_summary(conn),
    ]

    # Filter out empty strings and join
    return "\n\n".join(s for s in sections if s.strip())


# ---------------------------------------------------------------------------
# Briefing synthesis
# ---------------------------------------------------------------------------

async def generate_morning_briefing(
    router: "ProviderRouter",
    conn: sqlite3.Connection,
) -> str:
    """
    Build context from DB and generate a conversational morning briefing.

    Returns:
        A briefing string ready to be passed to the TTS engine.
        Targets < 120 spoken words.
    """
    context = build_briefing_context(conn)

    system = load_prompt("morning_briefing")

    messages = [
        {
            "role": "user",
            "content": (
                f"{context}\n\n"
                "Generate a friendly, motivating morning briefing. "
                "Keep it under 120 spoken words — synthesise, don't just list. "
                "Start with a greeting. Mention the most important task or event first. "
                "If the focus window is available, suggest when to tackle deep work."
            ),
        }
    ]

    briefing = await router.complete(
        "morning_briefing", messages, system=system, max_tokens=200
    )
    return briefing.strip()
