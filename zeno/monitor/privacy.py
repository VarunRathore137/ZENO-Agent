import fnmatch, sqlite3, sys
from typing import Any

def _load_exclusions(db_path: str) -> dict[str, list[str]]:
    """Load privacy_exclusions from DB. Never raises — returns empty dict on error."""
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT exclusion_type, value FROM privacy_exclusions"
            ).fetchall()
    except sqlite3.Error as e:
        print(f"[privacy] DB error loading exclusions: {e}", file=sys.stderr)
        return {}
    result: dict[str, list[str]] = {"app_name": [], "window_title_pattern": [], "browser_domain": []}
    for exc_type, value in rows:
        if exc_type in result:
            result[exc_type].append(value)
    return result

def is_excluded(app_name: str, window_title: str, db_path: str) -> bool:
    """Return True if this sample should be redacted."""
    exclusions = _load_exclusions(db_path)
    if not exclusions:
        return False
    # Exact app name match (case-insensitive)
    if any(app_name.lower() == ex.lower() for ex in exclusions["app_name"]):
        return True
    # Window title pattern match via fnmatch (% → * for LIKE-style patterns)
    for pattern in exclusions["window_title_pattern"]:
        py_pattern = pattern.replace("%", "*")
        if fnmatch.fnmatch(window_title.lower(), py_pattern.lower()):
            return True
    return False

def is_domain_excluded(domain: str, db_path: str) -> bool:
    """Return True if a browser domain should be excluded."""
    exclusions = _load_exclusions(db_path)
    return any(domain.lower() == ex.lower() for ex in exclusions.get("browser_domain", []))

def redact(sample: dict[str, Any], db_path: str) -> dict[str, Any]:
    """
    Return a copy of sample with app_name and window_title replaced by
    '[redacted]' if the sample matches any privacy exclusion.
    Never mutates the input dict.
    """
    if is_excluded(sample.get("app_name", ""), sample.get("window_title", ""), db_path):
        return {**sample, "app_name": "[redacted]", "window_title": "[redacted]"}
    return sample
