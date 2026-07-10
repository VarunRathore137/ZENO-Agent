"""
FastAPI server running on http://localhost:8766.
Started in a daemon thread alongside the Python voice/NLP pipeline.

React frontend fetches all dashboard data from this server.
Rust (Tauri) IPC is limited to window management — no DB reads in Rust.

Live monitoring:
    Get-Content -Path "$env:USERPROFILE\\Zeno\\logs\\zeno.log" -Wait
"""
import logging
import sqlite3
import threading
from pathlib import Path

import psutil
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 8766  # HTTP API port. WebSocket browser-extension is on 8765.

app = FastAPI(title="ZENO Daemon API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # Tauri webview origin is app://localhost or http://localhost:*
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory daemon state flags (toggled by tray menu)
# ---------------------------------------------------------------------------
_state: dict = {
    "focus_mode": False,
    "tts_muted": False,
    "db_path": "",
    "stop_event": None,        # set by ZenoDaemonAPI.start(); checked by /daemon/shutdown
}


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ---------------------------------------------------------------------------
# /system — real-time Windows metrics via psutil
# ---------------------------------------------------------------------------
@app.get("/system")
def get_system():
    cpu = psutil.cpu_percent(interval=0.2)

    mem = psutil.virtual_memory()
    ram_used_gb = round(mem.used / (1024 ** 3), 1)
    ram_total_gb = round(mem.total / (1024 ** 3), 1)

    battery = psutil.sensors_battery()
    battery_pct = round(battery.percent) if battery else None
    battery_plugged = battery.power_plugged if battery else None

    net = psutil.net_io_counters()
    # Single snapshot — caller can diff against previous call for speed
    net_bytes_sent = net.bytes_sent
    net_bytes_recv = net.bytes_recv

    # GPU: psutil doesn't support GPU natively; attempt via WMI on Windows
    gpu_pct = None
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=1
        )
        if result.returncode == 0:
            gpu_pct = int(result.stdout.strip().split()[0])
    except Exception:
        pass  # No GPU or nvidia-smi not present — returns null in response

    return {
        "cpu_percent": cpu,
        "ram_used_gb": ram_used_gb,
        "ram_total_gb": ram_total_gb,
        "ram_percent": round(mem.percent),
        "battery_percent": battery_pct,
        "battery_plugged": battery_plugged,
        "gpu_percent": gpu_pct,
        "net_bytes_sent": net_bytes_sent,
        "net_bytes_recv": net_bytes_recv,
        "focus_mode": _state["focus_mode"],
        "tts_muted": _state["tts_muted"],
    }


# ---------------------------------------------------------------------------
# /tasks — today's tasks
# ---------------------------------------------------------------------------
@app.get("/tasks")
def get_tasks():
    db_path = _state["db_path"]
    if not db_path:
        return {"tasks": []}
    try:
        with _db(db_path) as conn:
            rows = conn.execute(
                "SELECT id, title, priority, status, due_date FROM v_todays_tasks "
                "ORDER BY priority DESC, due_date ASC"
            ).fetchall()
        return {"tasks": [dict(r) for r in rows]}
    except Exception as e:
        logger.error("get_tasks error: %s", e)
        return {"tasks": [], "error": str(e)}


# ---------------------------------------------------------------------------
# /briefing — today's session file
# ---------------------------------------------------------------------------
@app.get("/briefing")
def get_briefing():
    db_path = _state["db_path"]
    zeno_dir = Path(db_path).parent if db_path else Path.home() / "Zeno"
    from datetime import date
    today = date.today().isoformat()
    session_path = zeno_dir / "sessions" / f"{today}.md"
    content = session_path.read_text(encoding="utf-8") if session_path.exists() else ""
    return {"date": today, "content": content, "path": str(session_path)}


# ---------------------------------------------------------------------------
# /analytics — 7-day activity breakdown
# ---------------------------------------------------------------------------
@app.get("/analytics")
def get_analytics():
    db_path = _state["db_path"]
    if not db_path:
        return {"analytics": []}
    try:
        with _db(db_path) as conn:
            rows = conn.execute("""
                SELECT
                    date(sampled_at) AS day,
                    COUNT(*) * 30 / 60      AS total_minutes,
                    SUM(CASE WHEN input_level IN ('heavy','moderate') AND is_off_task=0
                        THEN 30 ELSE 0 END) / 60 AS deep_work_minutes,
                    SUM(CASE WHEN is_off_task=1 THEN 30 ELSE 0 END) / 60 AS distraction_minutes,
                    SUM(CASE WHEN input_level='idle' THEN 30 ELSE 0 END) / 60 AS idle_minutes
                FROM activity_log
                WHERE sampled_at >= date('now','-7 days')
                GROUP BY day
                ORDER BY day ASC
            """).fetchall()
        return {"analytics": [dict(r) for r in rows]}
    except Exception as e:
        logger.error("get_analytics error: %s", e)
        return {"analytics": [], "error": str(e)}


# ---------------------------------------------------------------------------
# /settings — user_profile row
# ---------------------------------------------------------------------------
@app.get("/settings")
def get_settings():
    db_path = _state["db_path"]
    if not db_path:
        return {"settings": {}}
    try:
        with _db(db_path) as conn:
            row = conn.execute(
                "SELECT user_name, wake_word, tts_engine, stt_model, claude_model, "
                "working_hours_start, working_hours_end, timezone FROM user_profile LIMIT 1"
            ).fetchone()
        return {"settings": dict(row) if row else {}}
    except Exception as e:
        logger.error("get_settings error: %s", e)
        return {"settings": {}, "error": str(e)}


# ---------------------------------------------------------------------------
# Daemon control endpoints (called by Tauri tray menu via HTTP POST)
# ---------------------------------------------------------------------------
@app.post("/daemon/focus")
def toggle_focus():
    _state["focus_mode"] = not _state["focus_mode"]
    mode = "ON" if _state["focus_mode"] else "OFF"
    logger.info("Focus mode toggled: %s", mode)
    return {"focus_mode": _state["focus_mode"], "label": f"Focus Mode: {mode}"}


@app.post("/daemon/tts/mute")
def toggle_tts_mute():
    _state["tts_muted"] = not _state["tts_muted"]
    state = "MUTED" if _state["tts_muted"] else "ACTIVE"
    logger.info("TTS %s", state)
    return {"tts_muted": _state["tts_muted"], "label": f"Voice: {state}"}


@app.post("/daemon/shutdown")
def shutdown_daemon():
    logger.info("Shutdown requested via API.")
    stop_event = _state.get("stop_event")
    if stop_event is not None:
        stop_event.set()
    return {"status": "shutting_down"}


# ---------------------------------------------------------------------------
# ZenoDaemonAPI — thread wrapper called from __main__.py
# ---------------------------------------------------------------------------
class ZenoDaemonAPI:
    """
    Wraps the FastAPI/uvicorn server in a daemon thread.

    Usage in __main__.py:
        api = ZenoDaemonAPI(db_path=db_path, stop_event=stop_event)
        api.start()
    """

    def __init__(self, db_path: str, stop_event: threading.Event) -> None:
        _state["db_path"] = db_path
        _state["stop_event"] = stop_event
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="ZenoDaemonAPI"
        )

    def start(self) -> None:
        self._thread.start()
        logger.info("ZENO API server starting on http://%s:%d", HOST, PORT)

    def _run(self) -> None:
        config = uvicorn.Config(
            app,
            host=HOST,
            port=PORT,
            log_level="warning",   # suppress uvicorn access spam; use zeno logger for app logs
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        server.run()
