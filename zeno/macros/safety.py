import sqlite3
import sys
from typing import NamedTuple

class MacroSafetyError(Exception):
    pass

class SafetyResult(NamedTuple):
    allowed: bool
    reason: str
    message: str

def check_app_safety(app_name: str, db_path: str) -> SafetyResult:
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT is_work_app, user_override FROM app_classifications "
                "WHERE app_name = ? COLLATE NOCASE LIMIT 1",
                (app_name,)
            ).fetchone()
            
        if row is None:
            # Unknown — warn and allow
            return SafetyResult(
                allowed=True,
                reason="warn_unknown",
                message=f"'{app_name}' isn't in my app registry. I'll open it anyway — say 'Allow {app_name} in macros' to register it."
            )
        is_work, override = row
        if override == 1 or is_work == 1:
            return SafetyResult(allowed=True, reason="allowed", message="")
        
        # Explicitly non-work, no override → hard deny
        return SafetyResult(
            allowed=False,
            reason="denied",
            message=f"'{app_name}' is classified as a non-work app and is blocked from macros. Say 'Allow {app_name} in macros' to override."
        )
    except sqlite3.Error as e:
        print(f"DB error: {e}", file=sys.stderr)
        return SafetyResult(
            allowed=True,
            reason="warn_unknown",
            message="DB error, proceeding anyway"
        )

def assert_app_allowed(app_name: str, db_path: str) -> SafetyResult:
    result = check_app_safety(app_name, db_path)
    if result.reason == "denied":
        raise MacroSafetyError(result.message)
    return result

def register_app(app_name: str, db_path: str, is_work_app: bool = True, user_override: bool = False) -> None:
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO app_classifications (app_name, category, is_work_app, user_override) VALUES (?, 'utility', ?, ?)",
                (app_name, is_work_app, user_override)
            )
            conn.execute(
                "UPDATE app_classifications SET is_work_app=?, user_override=?, confidence=1.0 WHERE app_name=? COLLATE NOCASE",
                (is_work_app, user_override, app_name)
            )
    except sqlite3.Error as e:
        print(f"DB error: {e}", file=sys.stderr)
