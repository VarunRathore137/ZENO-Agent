from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import shutil, sys
import yaml

VALID_STEP_TYPES = frozenset({
    "open_app", "open_url", "focus_window",
    "arrange_windows", "toggle_dnd", "announce", "wait_ms",
})

# Path to the bundled template (same directory as this module's package root)
_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "workspaces.yaml"

@dataclass
class MacroStep:
    type: str
    params: dict[str, Any] = field(default_factory=dict)

@dataclass
class Workspace:
    id: str
    name: str
    description: str
    steps: list[MacroStep]

def _default_yaml_path() -> Path:
    return Path.home() / "Zeno" / "workspaces.yaml"

def load_workspaces(
    yaml_path: str | None = None,
    tts_worker=None,
) -> dict[str, Workspace]:
    """
    Parse workspaces.yaml into a dict of Workspace objects.

    Bootstrap behaviour:
    - If file missing: auto-create from bundled template, announce via TTS.
    - If file exists but is malformed YAML: raise ValueError (user error).
    - Never raises on missing file.
    """
    path = Path(yaml_path) if yaml_path else _default_yaml_path()

    if not path.exists():
        # First-run bootstrap
        path.parent.mkdir(parents=True, exist_ok=True)
        if _TEMPLATE_PATH.exists():
            shutil.copy(_TEMPLATE_PATH, path)
        else:
            # Fallback: write minimal template inline
            path.write_text(_MINIMAL_TEMPLATE, encoding="utf-8")
        msg = f"I've created a default workspaces file at {path} — you can customise it anytime."
        if tts_worker is not None:
            tts_worker.enqueue(msg)
        else:
            print(f"[Loader] {msg}")

    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"workspaces.yaml is malformed: {e}") from e

    workspaces: dict[str, Workspace] = {}
    for ws_id, ws_data in (data.get("workspaces") or {}).items():
        steps = []
        for raw_step in (ws_data.get("steps") or []):
            step_type = raw_step.get("type", "")
            if step_type not in VALID_STEP_TYPES:
                raise ValueError(f"Unknown step type '{step_type}' in workspace '{ws_id}'")
            params = {k: v for k, v in raw_step.items() if k != "type"}
            steps.append(MacroStep(type=step_type, params=params))
        workspaces[ws_id] = Workspace(
            id=ws_id,
            name=ws_data.get("name", ws_id),
            description=ws_data.get("description", ""),
            steps=steps,
        )
    return workspaces

def get_workspace(name: str, yaml_path: str | None = None, tts_worker=None) -> Workspace:
    workspaces = load_workspaces(yaml_path, tts_worker=tts_worker)
    if name not in workspaces:
        raise KeyError(f"Workspace '{name}' not found. Available: {list(workspaces.keys())}")
    return workspaces[name]

_MINIMAL_TEMPLATE = """workspaces:
  coding:
    name: "Coding Setup"
    description: "Default coding workspace"
    steps:
      - type: announce
        message: "Setting up your coding workspace."
"""
