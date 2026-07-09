import sqlite3, sys, threading
from zeno.monitor.privacy import redact

try:
    import win32gui, win32process, win32api
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


def _get_active_window() -> tuple[str, str]:
    """Returns (app_name, window_title). Falls back to ('unknown','unknown') on error."""
    if not (_WIN32_AVAILABLE and _PSUTIL_AVAILABLE):
        return ("unknown", "unknown")
    try:
        hwnd = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        app_name = psutil.Process(pid).name().removesuffix(".exe")
        return (app_name, window_title)
    except Exception:
        return ("unknown", "unknown")


def _compute_input_level() -> str:
    """
    Compute input level from GetLastInputInfo() idle time.
    No keyboard hooks — uses only time-since-last-input (mouse OR keyboard).
    Returns one of: 'idle', 'light', 'moderate', 'heavy'.
    """
    if not _WIN32_AVAILABLE:
        return "idle"
    try:
        last_input = win32api.GetLastInputInfo()  # returns dwTime (ms since boot)
        idle_ms = win32api.GetTickCount() - last_input
        if idle_ms > 60_000:  return "idle"
        if idle_ms > 10_000:  return "light"
        if idle_ms > 2_000:   return "moderate"
        return "heavy"
    except Exception:
        return "idle"


def _is_off_task(app_name: str, db_path: str) -> int:
    """
    Returns 1 if app is explicitly classified non-work (is_work_app=0, user_override=0).
    Unknown apps return 0 — warn-and-allow philosophy from Phase 7.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT is_work_app, user_override FROM app_classifications "
                "WHERE app_name = ? COLLATE NOCASE LIMIT 1",
                (app_name,)
            ).fetchone()
        if row and row[0] == 0 and row[1] == 0:
            return 1
        return 0
    except Exception:
        return 0


class ActivityMonitor:
    """
    Daemon thread that samples the active window every 30 seconds.
    Writes one row to activity_log per tick after privacy redaction.
    Context switches are NOT written here — derive them at query time
    from consecutive rows with different app_name values.
    """
    INTERVAL = 30  # seconds

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="ActivityMonitor"
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _loop(self) -> None:
        # Wait first so we don't fire immediately on startup
        while not self._stop_event.wait(timeout=self.INTERVAL):
            self._tick()

    def _tick(self) -> None:
        app_name, window_title = _get_active_window()
        input_level = _compute_input_level()
        is_off_task = _is_off_task(app_name, self._db_path)

        sample = redact(
            {"app_name": app_name, "window_title": window_title},
            self._db_path
        )

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO activity_log "
                    "(app_name, window_title, input_level, is_off_task) "
                    "VALUES (?, ?, ?, ?)",
                    (sample["app_name"], sample["window_title"],
                     input_level, is_off_task)
                )
        except Exception as e:
            print(f"[ActivityMonitor] DB write error: {e}", file=sys.stderr)
        # Never raise — one failed tick must not kill the monitor
