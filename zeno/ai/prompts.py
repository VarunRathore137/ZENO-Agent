"""
zeno/ai/prompts.py — YAML-based prompt template loader.

Prompt templates live in ~/Zeno/prompts/<template_name>.yaml
Each YAML file must have at minimum a 'text' key holding the prompt string.

Example YAML (~/Zeno/prompts/morning_briefing.yaml):
  name: morning_briefing
  description: Daily morning briefing system prompt
  text: |
    You are ZENO, a personal AI assistant for developers.
    Today is {date}. Here is the context for the morning briefing:
    {context}
    Generate a concise briefing under 120 spoken words.

Usage:
  from zeno.ai.prompts import load_prompt
  system = load_prompt("morning_briefing", date="2026-07-02", context=ctx)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Hardcoded fallback prompts — used when the YAML file does not exist.
# These are intentionally minimal; the real, tuned prompts belong in YAML.
# ---------------------------------------------------------------------------

_FALLBACK_PROMPTS: dict[str, str] = {
    "morning_briefing": (
        "You are ZENO, a personal AI assistant. "
        "Generate a concise morning briefing (under 120 spoken words) from the provided context."
    ),
    "rubber_duck_question": (
        "You are ZENO's Rubber Duck Mode facilitator. "
        "Guide the user through clarifying their problem by asking one focused question at a time."
    ),
    "rubber_duck_extract": (
        "You are extracting structured information from the user's answer. "
        "Return ONLY a JSON object with the requested fields."
    ),
    "prd_generation": (
        "You are ZENO's PRD writer. Generate a concise Product Requirements Document "
        "followed by '---TASKS---' and a JSON array of actionable tasks. "
        "Only include tasks from explicitly stated scope."
    ),
    "slot_extraction": (
        "You are the ZENO NLP slot extractor. "
        "Extract the requested slot values from the user utterance and return them as JSON."
    ),
    "clarification": (
        "You are ZENO. Ask a single, clear clarifying question to resolve the user's ambiguous request."
    ),
    "weekly_insights": (
        "You are ZENO's analytics narrator. "
        "Summarise the week's data into a short narrative insight for the user."
    ),
}


def _get_prompts_dir() -> Path:
    """Return the path to the user's prompts directory (~~/Zeno/prompts/)."""
    return Path.home() / "Zeno" / "prompts"


def load_prompt(template_name: str, **kwargs: Any) -> str:
    """
    Load a prompt template by name and interpolate variables.

    Lookup order:
      1. ~/Zeno/prompts/<template_name>.yaml  (user-editable)
      2. Built-in fallback string from _FALLBACK_PROMPTS

    Args:
        template_name: Name of the prompt template (without .yaml extension).
        **kwargs: Variables to interpolate into the template text using str.format_map.

    Returns:
        The fully interpolated prompt string.

    Raises:
        KeyError: If the template is not found in YAML or fallbacks.
    """
    prompts_dir = _get_prompts_dir()
    yaml_path = prompts_dir / f"{template_name}.yaml"

    raw_text: str | None = None

    # --- Attempt 1: load from YAML file ---
    if yaml_path.exists():
        try:
            with yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            raw_text = data.get("text")
            if not raw_text:
                # YAML exists but has no 'text' key — fall through to fallback
                raw_text = None
        except yaml.YAMLError as exc:
            import sys
            print(
                f"Warning: Failed to parse prompt YAML '{yaml_path}': {exc}",
                file=sys.stderr,
            )

    # --- Attempt 2: built-in fallback ---
    if raw_text is None:
        if template_name not in _FALLBACK_PROMPTS:
            raise KeyError(
                f"Prompt template '{template_name}' not found. "
                f"Create ~/Zeno/prompts/{template_name}.yaml or add a fallback to prompts.py."
            )
        raw_text = _FALLBACK_PROMPTS[template_name]

    # --- Interpolate variables ---
    if kwargs:
        try:
            return raw_text.format_map(kwargs)
        except KeyError as exc:
            import sys
            print(
                f"Warning: Prompt template '{template_name}' references undefined variable {exc}. "
                "Returning unformatted template.",
                file=sys.stderr,
            )
            return raw_text

    return raw_text


def write_default_prompts() -> None:
    """
    Write the built-in fallback prompts to ~/Zeno/prompts/ as YAML files
    so users can discover and customise them.

    Only writes files that don't already exist (never overwrites user edits).
    """
    prompts_dir = _get_prompts_dir()
    prompts_dir.mkdir(parents=True, exist_ok=True)

    for name, text in _FALLBACK_PROMPTS.items():
        yaml_path = prompts_dir / f"{name}.yaml"
        if not yaml_path.exists():
            data = {
                "name": name,
                "description": f"Default prompt for {name.replace('_', ' ')} feature.",
                "text": text,
            }
            with yaml_path.open("w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
