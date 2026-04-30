---
phase: 1
plan: 1
wave: 1
---

# Plan 1.1: Project Scaffold & Directory Layout

## Objective
Bootstrap the ZENO Python project with a proper package structure, dependency manifest, and the `~/Zeno/` runtime directory layout. This gives every subsequent phase a consistent foundation to build on — all module paths, entry points, and packaging metadata established here.

## Context
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- STACK.md
- ARCHITECTURE.md

## Tasks

<task type="auto">
  <name>Create pyproject.toml and requirements.txt</name>
  <files>
    pyproject.toml
    requirements.txt
    requirements-dev.txt
  </files>
  <action>
    Create `pyproject.toml` at the repo root using the `[project]` table (PEP 621 style, no build backend needed — use `setuptools`):
    - name: "zeno"
    - version: "0.1.0"
    - python requires: ">=3.11"
    - description: "ZENO — Just A Rather Very Intelligent System"
    - dependencies: list all packages from STACK.md Backend section (anthropic, openai-whisper, sounddevice, pyaudio, pyttsx3, apscheduler==3.*, websockets, flask, icalendar, pyyaml, rapidfuzz, keyboard, pygetwindow, pywin32)
    - [project.scripts]: `zeno = "zeno.__main__:main"`

    Create `requirements.txt` as a flat pin-free list (same packages, one per line) for users who prefer pip install -r.
    Create `requirements-dev.txt` with: pytest, pytest-asyncio, black, ruff, mypy.

    Do NOT pin versions except apscheduler (>=3.10,<4).
    Do NOT include tauri/frontend deps here — those go in a separate frontend/ directory.
  </action>
  <verify>python -c "import tomllib; tomllib.loads(open('pyproject.toml').read()); print('OK')"</verify>
  <done>pyproject.toml parses without error; `[project.scripts]` entry exists; requirements.txt has at least 10 packages listed</done>
</task>

<task type="auto">
  <name>Scaffold Python package structure</name>
  <files>
    zeno/__init__.py
    zeno/__main__.py
    zeno/voice/__init__.py
    zeno/nlp/__init__.py
    zeno/ai/__init__.py
    zeno/dispatcher/__init__.py
    zeno/handlers/__init__.py
    zeno/macros/__init__.py
    zeno/tts/__init__.py
    zeno/monitor/__init__.py
    zeno/scheduler/__init__.py
  </files>
  <action>
    Create all `__init__.py` files (empty or with a single docstring) to establish the package hierarchy:
    - `zeno/` — root package, `__init__.py` exports `__version__ = "0.1.0"`
    - `zeno/__main__.py` — entry point stub: `def main(): print("ZENO starting...")` + `if __name__ == "__main__": main()`
    - All sub-package `__init__.py` files — empty with a module docstring describing purpose (e.g., `"""Voice pipeline module."""`)

    Follow naming convention from ARCHITECTURE.md: snake_case for all Python files and directories.
  </action>
  <verify>python -m zeno</verify>
  <done>`python -m zeno` prints "ZENO starting..." without ImportError; all 11 sub-package directories exist with __init__.py</done>
</task>

## Success Criteria
- [ ] `pyproject.toml` valid (tomllib parse passes)
- [ ] `python -m zeno` runs without error
- [ ] All 11 package directories created under `zeno/`
- [ ] `requirements.txt` and `requirements-dev.txt` present
