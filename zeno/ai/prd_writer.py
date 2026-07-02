"""
zeno/ai/prd_writer.py — PRD generation and task extraction from Rubber Duck sessions.

Design (from DECISIONS.md):
  - One LLM call generates BOTH the PRD Markdown and the JSON task array.
  - Output is split on the delimiter: ---TASKS---
  - Part 1 (Markdown PRD) is written to ~/Zeno/projects/<slug>/PRD.md
  - Part 2 (JSON) is parsed and INSERTed into the `tasks` table.
  - Fallback: if JSON parsing fails, extract `- [ ]` checkboxes from Part 1.
  - Prompt constraint: "Generate tasks ONLY from explicitly stated scope."
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from zeno.ai.prompts import load_prompt
from zeno.ai.rubber_duck import RubberDuckSession, save_session

if TYPE_CHECKING:
    from zeno.ai.providers import ProviderRouter


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TASK_DELIMITER = "---TASKS---"

# Required fields and their defaults for task insertion
_TASK_DEFAULTS: dict[str, Any] = {
    "title": "",
    "priority": "medium",
    "estimated_minutes": 60,
    "depends_on": None,
    "milestone": None,
    "notes": None,
    "project_slug": None,
}


# ---------------------------------------------------------------------------
# PRD generation
# ---------------------------------------------------------------------------

async def generate_prd(
    session: RubberDuckSession,
    router: "ProviderRouter",
    conn: sqlite3.Connection,
) -> tuple[str, list[dict]]:
    """
    Generate a PRD and extract tasks from a completed Rubber Duck session.

    Returns:
        (prd_markdown, tasks_list) where:
          - prd_markdown is the full PRD text
          - tasks_list is a list of task dicts written to SQLite
    """
    system = load_prompt("prd_generation")

    # Build session context for the LLM
    context_parts: list[str] = [
        f"Project: {session.project_slug}",
        f"Problem: {session.problem_statement}",
    ]
    if session.constraints:
        context_parts.append("Constraints:\n" + "\n".join(f"- {c}" for c in session.constraints))
    if session.edge_cases:
        context_parts.append("Edge Cases:\n" + "\n".join(f"- {e}" for e in session.edge_cases))
    if session.dependencies:
        context_parts.append("Dependencies:\n" + "\n".join(f"- {d}" for d in session.dependencies))
    if session.success_criteria:
        context_parts.append("Success Criteria:\n" + "\n".join(f"- {s}" for s in session.success_criteria))

    context = "\n\n".join(context_parts)

    messages = [
        {
            "role": "user",
            "content": (
                f"{context}\n\n"
                f"Generate a concise PRD in Markdown, then add exactly '{_TASK_DELIMITER}' on a new line, "
                "then a JSON array of task objects. "
                "The JSON must have this schema for each task:\n"
                '{"title": string, "priority": "low|medium|high", '
                '"estimated_minutes": int, "depends_on": list[string] | null, '
                '"milestone": string | null, "notes": string | null}\n\n'
                "CRITICAL: Generate tasks ONLY from explicitly stated scope, not implied scope."
            ),
        }
    ]

    # LLM call
    raw_response = await router.complete(
        "prd_generation", messages, system=system, max_tokens=4096
    )

    # --- Split on the delimiter ---
    if _TASK_DELIMITER in raw_response:
        parts = raw_response.split(_TASK_DELIMITER, maxsplit=1)
        prd_markdown = parts[0].strip()
        tasks_raw = parts[1].strip()
    else:
        # Delimiter missing — treat entire response as markdown, extract via fallback
        prd_markdown = raw_response.strip()
        tasks_raw = ""

    # --- Write PRD.md ---
    prd_path = _get_prd_path(session.project_slug)
    prd_path.parent.mkdir(parents=True, exist_ok=True)
    prd_path.write_text(prd_markdown, encoding="utf-8")

    # --- Parse tasks ---
    tasks = _parse_tasks_json(tasks_raw, project_slug=session.project_slug)
    if not tasks:
        # Fallback: extract checkboxes from Markdown
        tasks = _parse_tasks_checkbox(prd_markdown, project_slug=session.project_slug)

    # --- Insert tasks into DB ---
    inserted_tasks = _insert_tasks(tasks, conn)

    # --- Mark session complete ---
    session.slots_complete = True
    save_session(session, conn)
    conn.commit()

    return prd_markdown, inserted_tasks


# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------

def _get_prd_path(project_slug: str) -> Path:
    """Return the filesystem path for a project's PRD.md file."""
    base = Path.home() / "Zeno" / "projects" / project_slug
    return base / "PRD.md"


# ---------------------------------------------------------------------------
# Task parsers
# ---------------------------------------------------------------------------

def _parse_tasks_json(raw: str, project_slug: str) -> list[dict]:
    """Primary parser: extract tasks from the JSON block after the delimiter."""
    if not raw:
        return []

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines
            if not line.startswith("```")
        ).strip()

    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        tasks: list[dict] = []
        for item in data:
            if not isinstance(item, dict) or not item.get("title"):
                continue
            task = dict(_TASK_DEFAULTS)
            task.update(item)
            task["project_slug"] = project_slug
            tasks.append(task)
        return tasks
    except (json.JSONDecodeError, ValueError):
        return []


def _parse_tasks_checkbox(markdown: str, project_slug: str) -> list[dict]:
    """Fallback parser: extract `- [ ] Task title` patterns from Markdown."""
    pattern = re.compile(r"^[-*]\s+\[\s*\]\s+(.+)$", re.MULTILINE)
    matches = pattern.findall(markdown)
    tasks: list[dict] = []
    for title in matches:
        task = dict(_TASK_DEFAULTS)
        task["title"] = title.strip()
        task["project_slug"] = project_slug
        tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# DB insertion
# ---------------------------------------------------------------------------

def _insert_tasks(tasks: list[dict], conn: sqlite3.Connection) -> list[dict]:
    """INSERT tasks into the `tasks` SQLite table. Returns list of inserted tasks."""
    inserted: list[dict] = []
    for task in tasks:
        if not task.get("title"):
            continue
        try:
            conn.execute(
                """
                INSERT INTO tasks (title, priority, estimated_minutes, notes, status)
                VALUES (:title, :priority, :estimated_minutes, :notes, 'todo')
                """,
                {
                    "title": task["title"],
                    "priority": task.get("priority", "medium"),
                    "estimated_minutes": task.get("estimated_minutes", 60),
                    "notes": task.get("notes"),
                },
            )
            inserted.append(task)
        except sqlite3.Error:
            # Non-fatal: skip individual bad rows
            continue
    return inserted
