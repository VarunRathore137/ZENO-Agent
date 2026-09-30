"""
zeno/ai/memory.py
─────────────────
AI-powered persistent memory system for ZENO.

After each conversation turn, Gemini analyzes the dialogue and extracts
durable facts (ADD/UPDATE/REMOVE transactions) stored in Zeno.db.

Memory is injected into every system prompt as a "knowledge card" so
ZENO always knows who the user is without robotic references.

7 memory categories (same as Elysia — battle-tested taxonomy):
  identity    — who they are (name, role, background)
  preference  — likes, dislikes, habits
  goal        — what they're working toward
  project     — ongoing projects and their status
  relationship — people in their life
  emotional   — mood patterns, emotional milestones
  behavior    — behavioral patterns and routines
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("zeno.ai.memory")

# ---------------------------------------------------------------------------
# Recent dialogue buffer (for memory extraction)
# ---------------------------------------------------------------------------
_dialogue_buffer: List[Dict[str, str]] = []
_dialogue_lock = threading.Lock()
_is_consolidating = False

CATEGORIES = ["identity", "preference", "goal", "project", "relationship", "emotional", "behavior"]


def add_to_dialogue(role: str, text: str) -> None:
    """Add a dialogue turn to the buffer. role = 'user' | 'zeno'"""
    with _dialogue_lock:
        _dialogue_buffer.append({"role": role, "text": text})
        # Keep only last 20 turns to stay within token budget
        if len(_dialogue_buffer) > 20:
            _dialogue_buffer.pop(0)


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------
def _get_db_path() -> str:
    return os.environ.get("ZENO_DB_PATH", str(Path.home() / "Zeno" / "Zeno.db"))


def _ensure_memories_table() -> None:
    """Create memories table if it doesn't exist (safe to call multiple times)."""
    import sqlite3
    try:
        conn = sqlite3.connect(_get_db_path())
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id          TEXT PRIMARY KEY,
                category    TEXT NOT NULL CHECK(category IN ('identity','preference','goal','project','relationship','emotional','behavior')),
                text        TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning("Could not ensure memories table: %s", e)


def load_memories() -> List[Dict[str, Any]]:
    """Load all memories from Zeno.db."""
    import sqlite3
    _ensure_memories_table()
    try:
        conn = sqlite3.connect(_get_db_path())
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, category, text, created_at, updated_at FROM memories ORDER BY updated_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error("Failed to load memories: %s", e)
        return []


def save_memory_item(category: str, text: str, memory_id: Optional[str] = None) -> str:
    """Insert or update a single memory. Returns the id."""
    import sqlite3
    import uuid
    _ensure_memories_table()
    if memory_id is None:
        memory_id = str(uuid.uuid4())[:9]
    try:
        conn = sqlite3.connect(_get_db_path())
        conn.execute(
            "INSERT OR REPLACE INTO memories (id, category, text, updated_at) VALUES (?, ?, ?, datetime('now'))",
            (memory_id, category, text)
        )
        conn.commit()
        conn.close()
        log.info("Memory saved: [%s] %s", category, text[:60])
    except Exception as e:
        log.error("Failed to save memory: %s", e)
    return memory_id


def delete_memory(memory_id: str) -> None:
    """Delete a memory by id."""
    import sqlite3
    try:
        conn = sqlite3.connect(_get_db_path())
        conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        log.error("Failed to delete memory %s: %s", memory_id, e)


# ---------------------------------------------------------------------------
# Memory injection into system prompts
# ---------------------------------------------------------------------------
def format_memory_injection(base_prompt: str) -> str:
    """
    Inject persistent memory into a system prompt.
    Returns the enriched prompt.
    """
    memories = load_memories()

    if not memories:
        return (
            base_prompt
            + "\n\n=== ZENO MEMORY CORE ===\n"
            "You do not have any persistent recollections of this user yet. "
            "As you interact, pay attention to who they are, their projects, habits, and goals.\n"
            "========================\n"
        )

    # Group by category
    grouped: Dict[str, List[str]] = {}
    for m in memories:
        cat = m["category"]
        grouped.setdefault(cat, []).append(m["text"])

    category_labels = {
        "identity":     "Identity (Name, role, background)",
        "preference":   "Preferences & Tastes",
        "goal":         "Active Goals & Aspirations",
        "project":      "Ongoing Projects",
        "relationship": "Key People & Relationships",
        "emotional":    "Emotional Highlights & Milestones",
        "behavior":     "Behavioral Traits & Patterns",
    }

    block = (
        "\n\n=== ZENO PERSISTENT MEMORY (KNOWLEDGE CARD) ===\n"
        "You have interacted with this user before. The following are your persistent recollections.\n"
        "INTEGRATION RULES:\n"
        "- Reference memories naturally, like a friend who knows you well. Never say 'According to my records...' or 'My database shows...'\n"
        "- Use this context to be more helpful, relevant, and personal in your responses.\n\n"
        "CURRENT KNOWLEDGE CARD:\n"
    )

    for cat, label in category_labels.items():
        items = grouped.get(cat, [])
        if items:
            block += f"* {label}:\n"
            for item in items:
                block += f"  - {item}\n"

    block += "================================================\n"

    return base_prompt + block


# ---------------------------------------------------------------------------
# AI-powered memory extraction (post-turn)
# ---------------------------------------------------------------------------
def trigger_memory_extraction() -> None:
    """
    Called after each conversation turn.
    Runs Gemini to extract ADD/UPDATE/REMOVE memory transactions.
    Thread-safe — skips if already consolidating.
    """
    global _is_consolidating

    with _dialogue_lock:
        if _is_consolidating:
            log.debug("Memory consolidation already running — skipping")
            return
        if len(_dialogue_buffer) < 2:
            return
        dialogue_snapshot = list(_dialogue_buffer)

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return

    _is_consolidating = True
    try:
        _run_extraction(api_key, dialogue_snapshot)
    finally:
        _is_consolidating = False


def _run_extraction(api_key: str, dialogue: List[Dict[str, str]]) -> None:
    """Inner: call Gemini to produce memory transactions and apply them."""
    from google import genai
    from google.genai import types as gtypes

    current_memories = load_memories()
    memory_ctx = "\n".join(
        f"ID: {m['id']} | Category: {m['category']} | Fact: {m['text']}"
        for m in current_memories
    ) or "(No memories yet)"

    dialogue_ctx = "\n".join(
        f"{'User' if d['role'] == 'user' else 'ZENO'}: {d['text']}"
        for d in dialogue
    )

    prompt = f"""You are ZENO's deep memory extraction engine. Analyze the recent conversation and output memory transactions.

OBJECTIVE: Extract durable, personal facts. Ignore small talk, greetings, temporary states ("I'm tired right now"), or fleeting comments.

CURRENT MEMORIES:
{memory_ctx}

RECENT CONVERSATION:
{dialogue_ctx}

RULES:
- ADD: New personal information not in current memories
- UPDATE: Information that updates/corrects an existing memory (provide exact ID)
- REMOVE: Memory explicitly disproven or user asked to forget (provide exact ID)
- TEXT: Third-person declarative summary. E.g. "The user is building a personal AI assistant called ZENO."
- Only extract DURABLE, IMPORTANT facts. Not every message needs a transaction.

Categories: identity, preference, goal, project, relationship, emotional, behavior"""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.environ.get("ZENO_MEMORY_MODEL", "gemini-3.8-flash"),
            contents=prompt,
            config=gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "transactions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action":   {"type": "string", "enum": ["ADD", "UPDATE", "REMOVE"]},
                                    "id":       {"type": "string"},
                                    "category": {"type": "string", "enum": CATEGORIES},
                                    "text":     {"type": "string"},
                                },
                                "required": ["action", "category", "text"],
                            }
                        }
                    },
                    "required": ["transactions"],
                }
            )
        )

        data = json.loads(response.text or "{}")
        transactions = data.get("transactions", [])

        if not transactions:
            log.debug("Memory extraction: no transactions — routine conversation")
            return

        log.info("Memory extraction: applying %d transactions", len(transactions))

        for trx in transactions:
            action = trx.get("action")
            mem_id = trx.get("id")
            category = trx.get("category", "behavior")
            text = trx.get("text", "")

            if action == "ADD":
                save_memory_item(category, text)
            elif action == "UPDATE" and mem_id:
                save_memory_item(category, text, memory_id=mem_id)
            elif action == "REMOVE" and mem_id:
                delete_memory(mem_id)

        # Prune: keep only 100 most recent memories (generous vs Elysia's 50)
        _prune_memories(max_count=100)

    except Exception as e:
        log.error("Memory extraction failed: %s", e)


def _prune_memories(max_count: int = 100) -> None:
    """Keep only the N most recently updated memories."""
    import sqlite3
    try:
        conn = sqlite3.connect(_get_db_path())
        conn.execute(f"""
            DELETE FROM memories WHERE id NOT IN (
                SELECT id FROM memories ORDER BY updated_at DESC LIMIT {max_count}
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning("Memory pruning failed: %s", e)
