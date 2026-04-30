---
phase: 1
plan: 2
wave: 1
---

# Plan 1.2: SQLite Database Bootstrap

## Objective
Create the database connection factory and initialize `Zeno.db` from the existing `zeno_schema.sql` schema file. This is the single source of truth for all persistent state — every other module depends on it being present and correctly configured.

## Context
- .gsd/SPEC.md
- ARCHITECTURE.md
- zeno_schema.sql

## Tasks

<task type="auto">
  <name>Create zeno/db.py — SQLite connection factory</name>
  <files>
    zeno/db.py
  </files>
  <action>
    Create `zeno/db.py` with a `get_connection(db_path: str | None = None) -> sqlite3.Connection` factory function:
    - Default `db_path`: `Path.home() / "Zeno" / "Zeno.db"`
    - Apply PRAGMA settings exactly as spec: `journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`, `temp_store=MEMORY`, `mmap_size=268435456` (256MB)
    - Use `sqlite3.Row` as `row_factory` for dict-like row access
    - Register a custom `detect_types=sqlite3.PARSE_DECLTYPES` so `datetime` columns parse automatically
    - Expose a context manager `db_session()` using `contextlib.contextmanager` that auto-commits or rolls back

    Do NOT use any ORM. Raw `sqlite3` only (stdlib).
    Do NOT create the database file here — that is the job of `init_db()` in the next task.
  </action>
  <verify>python -c "from zeno.db import get_connection; print('import OK')"</verify>
  <done>Import succeeds; `get_connection` callable exists; `db_session` context manager importable</done>
</task>

<task type="auto">
  <name>Create scripts/init_db.py — Schema initializer</name>
  <files>
    scripts/init_db.py
  </files>
  <action>
    Create `scripts/init_db.py` that:
    1. Creates `~/Zeno/` directory and sub-directories (`sessions/`, `projects/`) if they don't exist
    2. Reads `zeno_schema.sql` from the repo root (use `Path(__file__).parent.parent / "zeno_schema.sql"`)
    3. Gets a connection via `zeno.db.get_connection()`
    4. Runs `conn.executescript(schema_sql)` to initialize all tables, views, triggers, and indexes
    5. Inserts a default `user_profile` row if none exists (reasonable defaults: `claude_model='claude-sonnet-4'`, `tts_engine='pyttsx3'`, `stt_model='whisper-base'`, `wake_word='Hey Zeno'`, `timezone='UTC'`, `working_hours_start='09:00'`, `working_hours_end='18:00'`)
    6. Prints a success summary: tables created, DB path

    The script must be idempotent — re-running on an existing DB must not error (schema uses `CREATE TABLE IF NOT EXISTS`).
    Add `if __name__ == "__main__":` guard.
  </action>
  <verify>python scripts/init_db.py && python -c "import sqlite3; c=sqlite3.connect('C:/Users/' + __import__('os').environ['USERNAME'] + '/Zeno/Zeno.db'); print(c.execute('SELECT name FROM sqlite_master WHERE type=\'table\'').fetchall())"</verify>
  <done>Script runs without error; `Zeno.db` file exists at `~/Zeno/Zeno.db`; at least 20 tables are present when queried; re-running the script does not raise an error</done>
</task>

## Success Criteria
- [ ] `from zeno.db import get_connection, db_session` imports cleanly
- [ ] `python scripts/init_db.py` creates `~/Zeno/Zeno.db` with 22+ tables
- [ ] Script is idempotent (can be run twice without error)
- [ ] WAL mode confirmed: `PRAGMA journal_mode;` returns `wal`
