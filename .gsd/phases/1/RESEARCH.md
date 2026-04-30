---
phase: 1
level: 2
researched_at: 2026-04-30
---

# Phase 1 Research — Project Scaffold & Database Bootstrap

## Questions Investigated

1. What is the modern Python project layout for a long-lived daemon application on Windows?
2. Should we use `pyproject.toml` alone or keep a companion `requirements.txt`? What build backend?
3. How should `zeno/db.py` implement the SQLite connection factory given WAL mode and multi-threading?
4. How should `zeno/config.py` implement the YAML loader and `user_profile` singleton sync?
5. What is the correct directory layout for `~/Zeno/` and the Python source tree?
6. How do we handle PRAGMAs that must be re-applied on every new connection?

---

## Findings

### 1. Python Project Layout

**Recommendation: flat `zeno/` package at repo root (not `src/` layout).**

The `src/` layout is best for installable libraries. ZENO is a run-in-place daemon — it will be launched via `python -m zeno` or a `zeno.exe` entry point and will never be published to PyPI. The flat layout (`zeno/` sitting at the repo root) is simpler and avoids requiring `pip install -e .` for development.

**Sources:**
- https://realpython.com/python-application-layouts/
- https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/

**Recommended repo-level structure:**

```
ZENO-My-Personal-Assisstant/     ← repo root
├── pyproject.toml
├── requirements.txt              ← pip-installable deps (generated from pyproject.toml extras)
├── zeno/                         ← main Python package
│   ├── __init__.py
│   ├── __main__.py               ← entry point: python -m zeno
│   ├── db.py
│   ├── config.py
│   ├── voice/
│   ├── nlp/
│   ├── ai/
│   ├── dispatcher/
│   ├── handlers/
│   ├── macros/
│   ├── tts/
│   ├── monitor/
│   └── scheduler/
├── tests/
└── .gsd/
```

The `~/Zeno/` user data directory (Zeno.db, config.yaml, sessions/, etc.) is separate from the source tree — resolved at runtime via `pathlib.Path.home() / "Zeno"`.

---

### 2. pyproject.toml vs requirements.txt

**Use `pyproject.toml` as the single source of truth. Keep a thin `requirements.txt` for `pip install -r` convenience (CI, Windows venv setup).**

- Build backend: **Hatchling** — clean defaults, no C extensions needed, modern PEP 517/621 compliant.
- Dev extras (`[project.optional-dependencies]`) for pytest, ruff, mypy, black.
- Pin Python ≥ 3.11 (required for `tomllib` stdlib, match statements, and modern `sqlite3` features).
- `requirements.txt` generated via `pip freeze` or maintained manually as a subset for quick venv bootstrap.

**Sources:**
- https://hatch.pypa.io/latest/config/metadata/
- https://packaging.python.org/en/latest/guides/writing-pyproject-toml/

**Key pyproject.toml sections:**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "zeno"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic",
    "openai-whisper",
    "sounddevice",
    "pyttsx3",
    "apscheduler>=3.10",
    "websockets",
    "icalendar",
    "pyyaml",
    "rapidfuzz",
    "pydantic>=2.0",
    "python-dotenv",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "black", "ruff", "mypy"]

[project.scripts]
zeno = "zeno.__main__:main"
```

**Note:** `openai-whisper` installs heavy ML deps (torch, etc.) — acceptable since ZENO is a local desktop app, not a server. Consider documenting install time in README.

---

### 3. SQLite Connection Factory (`zeno/db.py`)

**Core design decisions:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Threading model | Thread-local connections via `threading.local()` | Safest for a multi-threaded daemon (voice thread, scheduler thread, monitor thread all need DB) |
| `check_same_thread` | `True` (each thread gets its own conn) | Avoid complex locking; WAL allows concurrent readers natively |
| PRAGMAs | Re-applied on every `get_connection()` call | PRAGMAs are connection-scoped, not DB-file-scoped |
| Row factory | `sqlite3.Row` | Column-name access; no ORM needed for Phase 1 |
| Schema init | `executescript()` with `zeno_schema.sql` | Single idempotent bootstrap — all DDL uses `CREATE IF NOT EXISTS` |
| DB path | `pathlib.Path.home() / "Zeno" / "Zeno.db"` | Matches spec; no hardcoding |

**Sources:**
- https://docs.python.org/3/library/sqlite3.html#sqlite3.threadsafety
- https://emschwartz.me/sqlite-wal-and-multiple-processes/

**Pattern skeleton:**

```python
# zeno/db.py
import sqlite3
import threading
from pathlib import Path

_local = threading.local()

def _zeno_dir() -> Path:
    p = Path.home() / "Zeno"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection with WAL + FK PRAGMAs applied."""
    if not hasattr(_local, "conn") or _local.conn is None:
        db_path = _zeno_dir() / "Zeno.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")
        conn.execute("PRAGMA busy_timeout=5000")  # avoid SQLITE_BUSY on write contention
        _local.conn = conn
    return _local.conn

def close_connection() -> None:
    """Close the thread-local connection (call at thread exit)."""
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None

def init_schema() -> None:
    """Run zeno_schema.sql to bootstrap all tables. Safe to call on every startup (IF NOT EXISTS)."""
    schema_path = Path(__file__).parent.parent / "zeno_schema.sql"
    conn = get_connection()
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)
```

**Risk:** `executescript()` issues an implicit COMMIT before running — acceptable here since schema init runs once at startup before any app logic.

---

### 4. YAML Config Loader + `user_profile` Singleton (`zeno/config.py`)

**Design: Module-level singleton. Load `config.yaml` once; sync bidirectionally with `user_profile` DB row.**

Key points:
- Use `yaml.safe_load()` — never `yaml.load()`.
- Config object backed by **Pydantic v2** `BaseModel` for type safety and IDE autocompletion.
- `user_profile` table is a singleton (enforced by `CHECK (id = 1)` in schema) — always upsert row `id=1`.
- `config.yaml` is human-editable; `user_profile` is runtime source of truth. On startup: load YAML → upsert `user_profile` → read back resolved row.
- API keys (`ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`) come from environment variables via `python-dotenv`, **never** `config.yaml`.

**Sources:**
- https://docs.pydantic.dev/latest/
- https://pyyaml.org/wiki/PyYAMLDocumentation

**Pattern skeleton:**

```python
# zeno/config.py
import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()  # loads .env if present

class ZenoConfig(BaseModel):
    name: str = "User"
    wake_word: str = "Hey Zeno"
    working_hours_start: str = "09:00"
    working_hours_end: str = "19:00"
    tts_engine: str = "pyttsx3"
    stt_model: str = "whisper-base"
    claude_model: str = "claude-sonnet-4"
    timezone: str = "UTC"

    # Runtime-only (from env, not yaml)
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    elevenlabs_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY"))

_config: Optional[ZenoConfig] = None

def load_config() -> ZenoConfig:
    global _config
    if _config is not None:
        return _config
    config_path = Path.home() / "Zeno" / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    _config = ZenoConfig(**data)
    return _config

def sync_user_profile(conn) -> None:
    """Upsert the user_profile singleton row from loaded config."""
    cfg = load_config()
    conn.execute("""
        INSERT INTO user_profile (id, name, wake_word, working_hours_start, working_hours_end,
                                   tts_engine, stt_model, claude_model, timezone)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            wake_word=excluded.wake_word,
            working_hours_start=excluded.working_hours_start,
            working_hours_end=excluded.working_hours_end,
            tts_engine=excluded.tts_engine,
            stt_model=excluded.stt_model,
            claude_model=excluded.claude_model,
            timezone=excluded.timezone,
            updated_at=datetime('now')
    """, (cfg.name, cfg.wake_word, cfg.working_hours_start, cfg.working_hours_end,
          cfg.tts_engine, cfg.stt_model, cfg.claude_model, cfg.timezone))
    conn.commit()
```

---

### 5. `~/Zeno/` Directory Bootstrap

Phase 1 must create the user data directory tree if it doesn't exist. This is a one-liner with `pathlib`:

```python
def bootstrap_zeno_dir() -> Path:
    base = Path.home() / "Zeno"
    for subdir in ["sessions", "projects", "voice", "nlp", "ai",
                   "dispatcher", "macros", "tts", "monitor", "scheduler", "extension"]:
        (base / subdir).mkdir(parents=True, exist_ok=True)
    return base
```

And write a default `config.yaml` if not present:

```python
DEFAULT_CONFIG_YAML = """\
name: User
wake_word: "Hey Zeno"
working_hours_start: "09:00"
working_hours_end: "19:00"
tts_engine: pyttsx3
stt_model: whisper-base
claude_model: claude-sonnet-4
timezone: UTC
"""
```

---

### 6. Schema Initialization Risk: `executescript()` COMMIT Behavior

`conn.executescript()` in Python's `sqlite3` module issues an implicit `COMMIT` before running the script. This means:
- Cannot wrap `init_schema()` in a transaction started before the call.
- **Mitigation:** Run `init_schema()` as the very first operation at startup, before any transactional logic. This is safe since the schema is idempotent (`IF NOT EXISTS` throughout).

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Project layout | Flat `zeno/` at repo root | Daemon, not library; simpler dev workflow |
| Build backend | Hatchling | Modern, PEP 621, no C extensions needed |
| Config validation | Pydantic v2 BaseModel | Type safety, IDE autocompletion, clear schema |
| Config YAML loader | `yaml.safe_load()` | Security — no arbitrary code execution |
| API key storage | Environment variables via `python-dotenv` | Never in YAML |
| DB threading | Thread-local connections | Safe across voice/scheduler/monitor threads |
| Row factory | `sqlite3.Row` | Column-name access, no ORM overhead |
| PRAGMA application | On every `get_connection()` call | PRAGMAs are connection-scoped |
| `busy_timeout` | 5000 ms | Prevents immediate `SQLITE_BUSY` on write contention |
| Schema bootstrap | `executescript()` at startup | Idempotent, all DDL uses `IF NOT EXISTS` |

---

## Patterns to Follow

- Use `pathlib.Path` everywhere for paths — no string concatenation.
- Use `with conn:` context manager for all write transactions (auto-commit on success, rollback on exception).
- Keep `zeno/db.py` dependency-free (stdlib only) — no ORM.
- Keep `zeno/config.py` as the only import that touches environment variables.
- Every sub-package gets its own `__init__.py` even if empty — explicit is better than implicit.
- `zeno/__main__.py` is the only entry point — call `bootstrap_zeno_dir()` → `init_schema()` → `sync_user_profile()` in that order.

---

## Anti-Patterns to Avoid

- **`yaml.load()` without Loader:** Security risk — use `yaml.safe_load()` exclusively.
- **Sharing one connection across threads:** SQLite connections are not thread-safe for concurrent writes. Use thread-local pattern.
- **Hardcoding `~/Zeno/` as a string:** Use `Path.home() / "Zeno"` for cross-platform compatibility (macOS stretch goal).
- **Storing API keys in `config.yaml`:** Always from environment variables.
- **Running PRAGMAs only on DB creation:** PRAGMAs must be re-applied on every connection open.
- **Calling `executescript()` mid-transaction:** It implicitly commits — always run at startup before any business logic.

---

## Dependencies Identified

| Package | Version | Purpose |
|---------|---------|---------|
| `hatchling` | latest | Build backend (pyproject.toml) |
| `pyyaml` | >=6.0 | `config.yaml` loading |
| `pydantic` | >=2.0 | Config schema validation + type safety |
| `python-dotenv` | >=1.0 | `.env` file loading for API keys |
| `anthropic` | latest | Claude API (needed in later phases, declare now) |
| `openai-whisper` | latest | Whisper STT (Phase 2, declare now) |
| `sounddevice` | latest | Mic capture (Phase 2, declare now) |
| `pyttsx3` | latest | Default TTS (Phase 6, declare now) |
| `apscheduler` | >=3.10 | Scheduler (Phase 6, declare now) |
| `websockets` | latest | Browser extension WS server (Phase 8) |
| `icalendar` | latest | `.ics` calendar read/write |
| `rapidfuzz` | latest | Fuzzy name matching for slot resolution |
| `pytest` | latest (dev) | Unit testing |
| `ruff` | latest (dev) | Linting |
| `black` | latest (dev) | Formatting |
| `mypy` | latest (dev) | Static type checking |

---

## Risks

- **`openai-whisper` install size:** Pulls in PyTorch (~2GB). Document in README; suggest users pre-install torch separately if needed.
  - *Mitigation:* Mark whisper as optional in pyproject.toml extras (`[project.optional-dependencies]`); Phase 2 activates it. Phase 1 doesn't need it.
- **Windows path separator in SQL:** `zeno_schema.sql` uses Unix-style path in comment (`~/Zeno/Zeno.db`) but paths are never stored raw in SQL. No code risk.
- **`gen_grammar.js` hardcoded path:** `/home/claude/Zeno_VoiceGrammar.docx` — this is a doc generator, not runtime code. Not a Phase 1 concern but should be noted.
- **`notes_fts` UPDATE trigger gap:** Schema comment in ARCHITECTURE.md notes FTS5 sync doesn't handle `UPDATE` of `tags` only. Monitor in Phase 4 when notes handlers are built.
- **Pydantic v1 vs v2:** Confirm `pydantic>=2.0` — API changed significantly between versions. All code should use `model_dump()` not `.dict()`.

---

## Ready for Planning

- [x] Project layout decided (flat `zeno/` package)
- [x] Build tooling decided (hatchling + pyproject.toml)
- [x] `db.py` pattern decided (thread-local, WAL, `sqlite3.Row`)
- [x] `config.py` pattern decided (Pydantic v2 + `yaml.safe_load` + env vars)
- [x] Directory bootstrap strategy clear (`pathlib`, idempotent)
- [x] All Phase 1 dependencies identified
- [x] Risks catalogued with mitigations
