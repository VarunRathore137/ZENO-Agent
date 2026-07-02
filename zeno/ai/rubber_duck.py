"""
zeno/ai/rubber_duck.py — Hybrid Rubber Duck conversation state machine.

Architecture (as decided in .gsd/DECISIONS.md):
  - Python code owns STATE TRANSITIONS (via completion predicates).
  - LLM owns CONVERSATIONAL LANGUAGE and SLOT EXTRACTION.
  - SQLite owns PERSISTENCE (rubber_duck_sessions table).

6-state flow:
  PROBLEM → CONSTRAINTS → EDGE_CASES → DEPS → CRITERIA → GENERATING

Design principles:
  - Sessions survive daemon restarts (full DB serialisation).
  - Tiered context window: slots struct (always) + last 6 turns (sliding).
  - User can say "skip" to advance or "go back to <state>" to rewind.
"""

from __future__ import annotations

import asyncio
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from zeno.ai.prompts import load_prompt

if TYPE_CHECKING:
    from zeno.ai.providers import ProviderRouter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

State = Literal[
    "PROBLEM", "CONSTRAINTS", "EDGE_CASES", "DEPS", "CRITERIA", "GENERATING"
]

_STATE_ORDER: list[State] = [
    "PROBLEM", "CONSTRAINTS", "EDGE_CASES", "DEPS", "CRITERIA", "GENERATING"
]

# How many recent dialogue turns to keep in context window
_CONTEXT_WINDOW_TURNS = 6

# Number of turns before we summarise older history
_SUMMARISE_AFTER_TURNS = 20

# Command words that request a state skip
_SKIP_WORDS = {"skip", "next", "move on", "skip this", "pass"}


# ---------------------------------------------------------------------------
# Dataclass — the session struct
# ---------------------------------------------------------------------------

@dataclass
class RubberDuckSession:
    """
    Holds the complete state of a rubber duck session.
    Serialised to / deserialized from the `rubber_duck_sessions` SQLite table.
    """
    id: int = 0                                        # DB row id (0 = unsaved)
    project_slug: str = ""                             # e.g. "zeno-browser-ext"
    state: State = "PROBLEM"
    problem_statement: str = ""
    constraints: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    turn_history: list[dict] = field(default_factory=list)   # {"role", "content"}
    history_summary: str = ""                          # Summary of older turns
    slots_complete: bool = False
    created_at: str = ""
    updated_at: str = ""

    # ------------------------------------------------------------------
    # Completion predicates — the state machine checks these after each turn
    # ------------------------------------------------------------------

    def _is_state_complete(self, state: State) -> bool:
        """Return True when the required slots for *state* are populated."""
        if state == "PROBLEM":
            return bool(self.problem_statement.strip())
        if state == "CONSTRAINTS":
            return len(self.constraints) > 0
        if state == "EDGE_CASES":
            return len(self.edge_cases) > 0
        if state == "DEPS":
            return len(self.dependencies) > 0
        if state == "CRITERIA":
            return len(self.success_criteria) > 0
        if state == "GENERATING":
            return True
        return False

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    def _slots_context(self) -> str:
        """Return a compact summary of all populated slots for injection into prompts."""
        lines: list[str] = [f"=== Rubber Duck Session: {self.project_slug} ==="]
        if self.problem_statement:
            lines.append(f"Problem: {self.problem_statement}")
        if self.constraints:
            lines.append("Constraints:\n" + "\n".join(f"  - {c}" for c in self.constraints))
        if self.edge_cases:
            lines.append("Edge Cases:\n" + "\n".join(f"  - {e}" for e in self.edge_cases))
        if self.dependencies:
            lines.append("Dependencies:\n" + "\n".join(f"  - {d}" for d in self.dependencies))
        if self.success_criteria:
            lines.append("Success Criteria:\n" + "\n".join(f"  - {s}" for s in self.success_criteria))
        return "\n".join(lines)

    def _build_messages_for_llm(self) -> list[dict]:
        """
        Build the message list for an LLM call using the tiered context window.

        Tier 1: Slot struct (always injected as a system-level context block).
        Tier 2: Last _CONTEXT_WINDOW_TURNS turns.
        Tier 3: history_summary (if older turns were summarised).
        """
        messages: list[dict] = []

        # Inject summary of old history if it exists
        if self.history_summary:
            messages.append({
                "role": "user",
                "content": f"[Earlier session summary]\n{self.history_summary}",
            })
            messages.append({
                "role": "assistant",
                "content": "Understood. I have context from earlier in our session.",
            })

        # Inject the slot struct as a synthetic assistant "memory" message
        messages.append({
            "role": "user",
            "content": f"[Current session slots]\n{self._slots_context()}",
        })
        messages.append({
            "role": "assistant",
            "content": "Got it. I have the current session state.",
        })

        # Add recent turns
        recent = self.turn_history[-_CONTEXT_WINDOW_TURNS:]
        messages.extend(recent)

        return messages

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_db_dict(self) -> dict:
        """Return a dict suitable for INSERT/UPDATE into rubber_duck_sessions."""
        return {
            "project_slug": self.project_slug,
            "state": self.state,
            "problem_statement": self.problem_statement,
            "constraints": json.dumps(self.constraints),
            "edge_cases": json.dumps(self.edge_cases),
            "dependencies": json.dumps(self.dependencies),
            "success_criteria": json.dumps(self.success_criteria),
            "turn_history": json.dumps(self.turn_history),
            "history_summary": self.history_summary,
            "slots_complete": 1 if self.slots_complete else 0,
        }

    @classmethod
    def from_db_row(cls, row: sqlite3.Row) -> "RubberDuckSession":
        """Reconstruct a session from a SQLite Row."""
        def _loads(value: str | None) -> list:
            if not value:
                return []
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []

        return cls(
            id=row["id"],
            project_slug=row["project_slug"] or "",
            state=row["state"] or "PROBLEM",
            problem_statement=row["problem_statement"] or "",
            constraints=_loads(row["constraints"]),
            edge_cases=_loads(row["edge_cases"]),
            dependencies=_loads(row["dependencies"]),
            success_criteria=_loads(row["success_criteria"]),
            turn_history=_loads(row["turn_history"]),
            history_summary=row["history_summary"] or "",
            slots_complete=bool(row["slots_complete"]),
            created_at=str(row["created_at"] or ""),
            updated_at=str(row["updated_at"] or ""),
        )


# ---------------------------------------------------------------------------
# RubberDuckEngine — processes turns
# ---------------------------------------------------------------------------

class RubberDuckEngine:
    """
    Processes individual conversational turns for a RubberDuckSession.

    The engine:
      1. Detects skip/go-back commands.
      2. Calls the LLM to extract slots from the user's answer.
      3. Checks the completion predicate for the current state.
      4. Advances the state if complete.
      5. Calls the LLM to generate the next conversational question.
    """

    def __init__(self, router: "ProviderRouter") -> None:
        self._router = router

    async def process_turn(
        self,
        session: RubberDuckSession,
        user_input: str,
    ) -> str:
        """
        Process one user turn. Mutates *session* in place.

        Returns:
            The assistant's response text (next question or transition message).
        """
        # --- Handle meta-commands first ---
        normalised = user_input.strip().lower()

        if normalised in _SKIP_WORDS:
            return await self._skip_state(session)

        go_back_match = re.match(
            r"go back to (problem|constraints|edge cases|deps|criteria)",
            normalised,
        )
        if go_back_match:
            target_raw = go_back_match.group(1).upper().replace(" ", "_")
            if target_raw in _STATE_ORDER:
                session.state = target_raw  # type: ignore[assignment]
                return f"Going back to the {target_raw.replace('_', ' ').title()} phase. {await self._generate_question(session)}"

        # --- Append user turn to history ---
        session.turn_history.append({"role": "user", "content": user_input})

        # --- Summarise if history is getting long ---
        if len(session.turn_history) > _SUMMARISE_AFTER_TURNS:
            await self._summarise_old_history(session)

        # --- Extract slots for the current state ---
        await self._extract_slots(session, user_input)

        # --- Check completion predicate ---
        if session._is_state_complete(session.state):
            response = await self._advance_state(session)
        else:
            response = await self._generate_question(session)

        # --- Append assistant turn to history ---
        session.turn_history.append({"role": "assistant", "content": response})

        return response

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _extract_slots(self, session: RubberDuckSession, user_input: str) -> None:
        """Call the LLM to extract slot values from the user's answer and populate session."""
        state = session.state
        if state == "GENERATING":
            return  # Nothing to extract in final state

        schema_map: dict[State, dict] = {
            "PROBLEM":     {"problem_statement": "string — one or two sentence problem description"},
            "CONSTRAINTS": {"constraints": "list[string] — technical or business constraints"},
            "EDGE_CASES":  {"edge_cases": "list[string] — edge cases or failure modes"},
            "DEPS":        {"dependencies": "list[string] — external services, libraries, or teams"},
            "CRITERIA":    {"success_criteria": "list[string] — measurable success criteria"},
        }

        system = load_prompt("rubber_duck_extract")
        schema = schema_map.get(state, {})
        messages = [
            {
                "role": "user",
                "content": (
                    f"Current state: {state}\n"
                    f"User said: {user_input}\n\n"
                    f"Extract the following fields:\n{json.dumps(schema, indent=2)}\n\n"
                    "Return ONLY a JSON object."
                ),
            }
        ]

        try:
            result = await self._router.complete_structured("rubber_duck", messages, system=system)
        except Exception:
            return  # Slot extraction is best-effort; don't crash the turn

        # Merge extracted values into session
        if state == "PROBLEM" and result.get("problem_statement"):
            session.problem_statement = result["problem_statement"]
        elif state == "CONSTRAINTS" and result.get("constraints"):
            session.constraints.extend(
                c for c in result["constraints"] if c not in session.constraints
            )
        elif state == "EDGE_CASES" and result.get("edge_cases"):
            session.edge_cases.extend(
                e for e in result["edge_cases"] if e not in session.edge_cases
            )
        elif state == "DEPS" and result.get("dependencies"):
            session.dependencies.extend(
                d for d in result["dependencies"] if d not in session.dependencies
            )
        elif state == "CRITERIA" and result.get("success_criteria"):
            session.success_criteria.extend(
                s for s in result["success_criteria"] if s not in session.success_criteria
            )

    async def _advance_state(self, session: RubberDuckSession) -> str:
        """Advance to the next state and return a transition message + first question."""
        current_idx = _STATE_ORDER.index(session.state)
        if current_idx >= len(_STATE_ORDER) - 1:
            session.slots_complete = True
            return "All phases complete. Ready to generate your PRD."

        next_state: State = _STATE_ORDER[current_idx + 1]
        session.state = next_state

        transition = f"✓ Got it. Moving to **{next_state.replace('_', ' ').title()}**.\n\n"
        question = await self._generate_question(session)
        return transition + question

    async def _skip_state(self, session: RubberDuckSession) -> str:
        """Skip the current state (mark as empty, advance)."""
        current_idx = _STATE_ORDER.index(session.state)
        if current_idx >= len(_STATE_ORDER) - 1:
            session.slots_complete = True
            return "Skipped. All phases done. Ready to generate your PRD."

        skipped = session.state
        next_state: State = _STATE_ORDER[current_idx + 1]
        session.state = next_state
        return f"Skipping **{skipped.replace('_', ' ').title()}**. Moving to **{next_state.replace('_', ' ').title()}**.\n\n" + await self._generate_question(session)

    async def _generate_question(self, session: RubberDuckSession) -> str:
        """Ask the LLM to generate a conversational question for the current state."""
        system = load_prompt("rubber_duck_question")
        messages = session._build_messages_for_llm()
        messages.append({
            "role": "user",
            "content": (
                f"Current phase: {session.state}.\n"
                "Ask the user one focused, conversational question to gather the missing information for this phase."
            ),
        })
        try:
            return await self._router.complete("rubber_duck", messages, system=system, max_tokens=256)
        except Exception as exc:
            return f"[Error generating question: {exc}] Please describe your {session.state.lower().replace('_', ' ')}."

    async def _summarise_old_history(self, session: RubberDuckSession) -> None:
        """Summarise the oldest turns into session.history_summary to control context size."""
        old_turns = session.turn_history[:-_CONTEXT_WINDOW_TURNS]
        session.turn_history = session.turn_history[-_CONTEXT_WINDOW_TURNS:]

        if not old_turns:
            return

        summary_messages = [
            {
                "role": "user",
                "content": (
                    "Summarise the following conversation history in 3-4 sentences, "
                    "preserving key decisions and information:\n\n"
                    + "\n".join(
                        f"{t['role'].upper()}: {t['content']}" for t in old_turns
                    )
                ),
            }
        ]
        try:
            new_summary = await self._router.complete(
                "rubber_duck", summary_messages, max_tokens=256
            )
            if session.history_summary:
                session.history_summary = session.history_summary + "\n" + new_summary
            else:
                session.history_summary = new_summary
        except Exception:
            pass  # Keep old summary on error


# ---------------------------------------------------------------------------
# DB persistence helpers
# ---------------------------------------------------------------------------

def save_session(session: RubberDuckSession, conn: sqlite3.Connection) -> RubberDuckSession:
    """
    INSERT or UPDATE a RubberDuckSession in the `rubber_duck_sessions` table.
    Returns the session with `id` set.
    """
    data = session.to_db_dict()

    if session.id == 0:
        # New session — INSERT
        placeholders = ", ".join(f":{k}" for k in data)
        cols = ", ".join(data.keys())
        conn.execute(
            f"INSERT INTO rubber_duck_sessions ({cols}) VALUES ({placeholders})",
            data,
        )
        row = conn.execute(
            "SELECT last_insert_rowid() AS id"
        ).fetchone()
        session.id = row["id"]
    else:
        # Existing session — UPDATE
        set_clause = ", ".join(f"{k} = :{k}" for k in data)
        data["_id"] = session.id
        conn.execute(
            f"UPDATE rubber_duck_sessions SET {set_clause} WHERE id = :_id",
            data,
        )

    return session


def load_session(session_id: int, conn: sqlite3.Connection) -> RubberDuckSession | None:
    """Load a session from the DB by id. Returns None if not found."""
    row = conn.execute(
        "SELECT * FROM rubber_duck_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if row is None:
        return None
    return RubberDuckSession.from_db_row(row)


def load_latest_session(project_slug: str, conn: sqlite3.Connection) -> RubberDuckSession | None:
    """Load the most recent incomplete session for a project slug."""
    row = conn.execute(
        """
        SELECT * FROM rubber_duck_sessions
        WHERE project_slug = ? AND slots_complete = 0
        ORDER BY id DESC LIMIT 1
        """,
        (project_slug,),
    ).fetchone()
    if row is None:
        return None
    return RubberDuckSession.from_db_row(row)
