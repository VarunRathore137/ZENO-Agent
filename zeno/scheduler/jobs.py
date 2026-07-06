import asyncio, sys, sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

# -- Job 1: Morning Briefing --
def deliver_morning_briefing(db_path: str, ai_router, tts_worker) -> None:
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            from zeno.ai.briefing import generate_morning_briefing
            text = asyncio.run(generate_morning_briefing(ai_router, conn))
        tts_worker.enqueue(text)
    except Exception as e:
        print(f"[Scheduler] Briefing error: {e}", file=sys.stderr)

# -- Job 2: Reminder Firing --
def fire_due_reminders(db_path: str, tts_worker) -> None:
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, message FROM reminders "
                "WHERE trigger_at <= datetime('now') AND status = 'pending' LIMIT 10"
            ).fetchall()
            for row in rows:
                tts_worker.enqueue(row["message"])
                conn.execute("UPDATE reminders SET status='fired' WHERE id=?", (row["id"],))
            conn.commit()
    except Exception as e:
        print(f"[Scheduler] Reminder error: {e}", file=sys.stderr)

# -- Job 3: Weekly Analytics --
def regenerate_weekly_analytics(db_path: str) -> None:
    try:
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            existing = conn.execute(
                "SELECT 1 FROM analytics_weekly WHERE week_start = ?", (week_start,)
            ).fetchone()
            if existing:
                return  # idempotent — already computed this week
            # Aggregate from activity_log
            row = conn.execute("""
                SELECT
                    ROUND(SUM(CASE WHEN is_off_task=0 THEN 0.5/60.0 ELSE 0 END), 2) AS deep_work_hours
                FROM activity_log
                WHERE sampled_at >= ?
            """, (week_start,)).fetchone()
            tasks_done = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status='completed' AND updated_at >= ?",
                (week_start,)
            ).fetchone()[0]
            conn.execute(
                "INSERT OR REPLACE INTO analytics_weekly "
                "(week_start, deep_work_hours, tasks_completed, generated_at) "
                "VALUES (?, ?, ?, datetime('now'))",
                (week_start, row["deep_work_hours"] or 0.0, tasks_done)
            )
            conn.commit()
    except Exception as e:
        print(f"[Scheduler] Analytics error: {e}", file=sys.stderr)

# -- Jobs 4 & 5: Pomodoro --
def pomodoro_midpoint(tts_worker, duration_minutes: int) -> None:
    tts_worker.enqueue(
        f"Halfway through your {duration_minutes}-minute focus session. Keep going!"
    )

def pomodoro_end(tts_worker, duration_minutes: int) -> None:
    tts_worker.enqueue(
        f"Your {duration_minutes}-minute focus session is complete. Time for a break!"
    )
