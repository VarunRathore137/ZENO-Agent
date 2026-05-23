import sqlite3
import os
import sys
from pathlib import Path
from zeno.db import get_connection

def init_db():
    """
    Initialize the Zeno database from the schema file.
    Creates necessary directories and sets up initial data.
    """
    # 1. Create ~/Zeno/ directory and sub-directories
    zeno_dir = Path.home() / "Zeno"
    sub_dirs = ["sessions", "projects", "logs"]
    
    print(f"Ensuring Zeno directory structure at {zeno_dir}...")
    zeno_dir.mkdir(parents=True, exist_ok=True)
    for sub in sub_dirs:
        (zeno_dir / sub).mkdir(exist_ok=True)
    
    # 2. Read zeno_schema.sql
    schema_path = Path(__file__).parent.parent / "zeno_schema.sql"
    if not schema_path.exists():
        print(f"Error: Schema file not found at {schema_path}", file=sys.stderr)
        sys.exit(1)
        
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
        
    # 3. Get connection and 4. run schema
    db_path = zeno_dir / "Zeno.db"
    print(f"Initializing database at {db_path}...")
    
    try:
        conn = get_connection(db_path)
        conn.executescript(schema_sql)
        
        # 5. Insert default user_profile row if none exists
        # Check if profile exists
        cursor = conn.execute("SELECT COUNT(*) FROM user_profile")
        if cursor.fetchone()[0] == 0:
            print("Inserting default user profile...")
            conn.execute("""
                INSERT INTO user_profile (
                    id, name, wake_word, tts_engine, stt_model, claude_model, timezone
                ) VALUES (
                    1, 'User', 'Hey Zeno', 'pyttsx3', 'whisper-base', 'claude-sonnet-4', 'UTC'
                )
            """)
        
        conn.commit()
        
        # 6. Success summary
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Successfully initialized {len(tables)} tables.")
        print(f"Database is ready at {db_path}")
        
    except Exception as e:
        print(f"Error during database initialization: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_db()
