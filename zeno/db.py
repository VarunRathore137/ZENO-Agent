import sqlite3
import os
import contextlib
from pathlib import Path
from typing import Generator

def get_db_path() -> Path:
    """Get the default path to the Zeno database."""
    # Matches SPEC.md: ~/Zeno/Zeno.db
    base_dir = Path.home() / "Zeno"
    return base_dir / "Zeno.db"

def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """
    Create a connection to the SQLite database with optimized PRAGMA settings.
    """
    if db_path is None:
        db_path = get_db_path()
    
    # Ensure parent directory exists
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # PARSE_DECLTYPES allows automatic datetime parsing if columns are declared as TIMESTAMP/DATETIME
    conn = sqlite3.connect(
        str(db_path), 
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False # Allow access from multiple threads (e.g., dispatcher/monitor)
    )
    
    # dict-like row access
    conn.row_factory = sqlite3.Row
    
    # Apply PRAGMA settings per ARCHITECTURE.md and SPEC.md
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")  # 256MB
    
    return conn

@contextlib.contextmanager
def db_session(db_path: str | Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for a database session.
    Auto-commits on success, rolls back on exception.
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
