import os
import yaml
import sqlite3
from pathlib import Path
from typing import Any

def get_config_path() -> Path:
    """Get the path to the Zeno config file."""
    return Path.home() / "Zeno" / "config.yaml"

def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load the YAML configuration file.
    Falls back to safe defaults if the file is missing or unreadable.
    """
    if config_path is None:
        config_path = get_config_path()
        
    defaults = {
        "zeno": {
            "wake_word": "Hey Zeno",
            "claude_model": "claude-sonnet-4",
            "tts_engine": "pyttsx3",
            "stt_model": "whisper-base",
            "timezone": "UTC",
            "working_hours_start": "09:00",
            "working_hours_end": "18:00",
            "morning_briefing_time": "08:30"
        }
    }
    
    if not config_path.exists():
        return defaults
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            # Basic merge with defaults for safety
            if not config or "zeno" not in config:
                return defaults
            return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return defaults

def get_env_key(name: str) -> str | None:
    """
    Read API keys from environment variables.
    Never from the YAML file.
    """
    return os.environ.get(name)

def sync_to_db(config: dict[str, Any], conn: sqlite3.Connection) -> None:
    """
    Sync YAML configuration to the user_profile table in the database.
    """
    z_cfg = config.get("zeno", {})
    
    # Mapping of YAML keys to DB columns
    mapping = {
        "wake_word": z_cfg.get("wake_word"),
        "claude_model": z_cfg.get("claude_model"),
        "tts_engine": z_cfg.get("tts_engine"),
        "stt_model": z_cfg.get("stt_model"),
        "timezone": z_cfg.get("timezone"),
        "working_hours_start": z_cfg.get("working_hours_start"),
        "working_hours_end": z_cfg.get("working_hours_end")
    }
    
    # Filter out None values
    updates = {k: v for k, v in mapping.items() if v is not None}
    
    if not updates:
        return
        
    # Ensure a row exists (id=1 is singleton)
    conn.execute("INSERT OR IGNORE INTO user_profile (id) VALUES (1)")
    
    # Build UPDATE query
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values())
    
    query = f"UPDATE user_profile SET {set_clause} WHERE id = 1"
    conn.execute(query, values)
    conn.commit()

def get_setting(key: str, conn: sqlite3.Connection) -> Any:
    """
    Retrieve a setting from the user_profile table.
    """
    try:
        cursor = conn.execute(f"SELECT {key} FROM user_profile WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None
