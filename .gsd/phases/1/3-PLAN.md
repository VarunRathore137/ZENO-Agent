---
phase: 1
plan: 3
wave: 2
depends_on: ["2"]
---

# Plan 1.3: Config Layer — YAML + user_profile Sync

## Objective
Build the configuration layer: a `config.yaml` template for human-editable settings, and `zeno/config.py` that loads it and syncs to the `user_profile` SQLite singleton. This implements the "config duality" requirement from SPEC.md — SQLite is source of truth at runtime, YAML is for human editing between sessions.

**Wave 2 dependency:** Requires Plan 1.2 (database must exist before config can be synced to `user_profile` table).

## Context
- .gsd/SPEC.md (Config duality section)
- ARCHITECTURE.md (Conventions section)
- STACK.md (Configuration table)
- zeno/db.py (from Plan 1.2)

## Tasks

<task type="auto">
  <name>Create ~/Zeno/config.yaml default template</name>
  <files>
    scripts/create_config.py
    templates/config.yaml.template
  </files>
  <action>
    Create `templates/config.yaml.template` in the repo with all configurable keys and their defaults:
    ```yaml
    zeno:
      wake_word: "Hey Zeno"
      claude_model: "claude-sonnet-4"
      tts_engine: "pyttsx3"         # options: pyttsx3, elevenlabs, coqui
      stt_model: "whisper-base"     # options: whisper-tiny, whisper-base, whisper-small
      timezone: "UTC"               # e.g. "Asia/Kolkata"
      working_hours_start: "09:00"
      working_hours_end: "18:00"
      morning_briefing_time: "08:30"
    api_keys:
      anthropic: ""                 # Set ANTHROPIC_API_KEY env var instead
      elevenlabs: ""                # Set ELEVENLABS_API_KEY env var instead
    ```

    Create `scripts/create_config.py` that copies this template to `~/Zeno/config.yaml` if it doesn't already exist (never overwrite).
    Add idempotency: print "Config already exists, skipping" if file present.
  </action>
  <verify>python scripts/create_config.py && python -c "import yaml; d=yaml.safe_load(open(__import__('pathlib').Path.home() / 'Zeno/config.yaml')); print(d['zeno']['wake_word'])"</verify>
  <done>Running script creates `~/Zeno/config.yaml`; yaml.safe_load parses it without error; `d['zeno']['wake_word']` returns `'Hey Zeno'`</done>
</task>

<task type="auto">
  <name>Create zeno/config.py — Config loader with user_profile sync</name>
  <files>
    zeno/config.py
  </files>
  <action>
    Create `zeno/config.py` with:

    1. `load_config(config_path: Path | None = None) -> dict` — reads `~/Zeno/config.yaml` with `yaml.safe_load`, returns the parsed dict. Falls back to template defaults if file missing (do not crash).

    2. `get_env_key(name: str) -> str | None` — reads `ANTHROPIC_API_KEY` or `ELEVENLABS_API_KEY` from `os.environ`. Never read them from the YAML file (security).

    3. `sync_to_db(config: dict, conn: sqlite3.Connection) -> None` — does `INSERT OR IGNORE INTO user_profile DEFAULT VALUES` then `UPDATE user_profile SET` for each mapped key:
       - `wake_word` ← `config['zeno']['wake_word']`
       - `claude_model` ← `config['zeno']['claude_model']`
       - `tts_engine` ← `config['zeno']['tts_engine']`
       - `stt_model` ← `config['zeno']['stt_model']`
       - `timezone` ← `config['zeno']['timezone']`
       - `working_hours_start` ← `config['zeno']['working_hours_start']`
       - `working_hours_end` ← `config['zeno']['working_hours_end']`
       Only update keys that exist in the YAML (don't overwrite DB fields not in config).

    4. `get_setting(key: str, conn: sqlite3.Connection) -> str | None` — convenience: `SELECT <key> FROM user_profile LIMIT 1`

    Do NOT store API keys in the database. ANTHROPIC_API_KEY must only come from environment.
    Use type hints throughout. No global state — all functions take explicit arguments.
  </action>
  <verify>python -c "from zeno.config import load_config, sync_to_db; from zeno.db import get_connection; cfg=load_config(); conn=get_connection(); sync_to_db(cfg, conn); print('sync OK')"</verify>
  <done>Import succeeds; `sync_to_db` runs without error against initialized DB; `get_setting('wake_word', conn)` returns `'Hey Zeno'`</done>
</task>

## Success Criteria
- [ ] `~/Zeno/config.yaml` created by `scripts/create_config.py`
- [ ] `from zeno.config import load_config, sync_to_db, get_setting` imports cleanly
- [ ] `sync_to_db` populates `user_profile` table in DB
- [ ] API keys read exclusively from environment variables, not YAML
- [ ] Script is idempotent (re-running `create_config.py` does not overwrite existing config)
