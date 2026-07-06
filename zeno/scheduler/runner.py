import functools
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

class ZenoScheduler:
    def __init__(self, config: dict, db_path: str, ai_router, tts_worker) -> None:
        self._config = config
        self._db_path = db_path
        self._ai_router = ai_router
        self._tts_worker = tts_worker
        tz = config.get("zeno", {}).get("timezone", "UTC")
        self._scheduler = BackgroundScheduler(timezone=tz)
        self._running = False

    def start(self) -> None:
        from zeno.scheduler.scheduler_registry import register_static_jobs
        register_static_jobs(
            self._scheduler, self._config,
            self._db_path, self._ai_router, self._tts_worker
        )
        # Reminder polling — every minute, 5-minute misfire grace
        from zeno.scheduler.jobs import fire_due_reminders
        self._scheduler.add_job(
            functools.partial(fire_due_reminders, self._db_path, self._tts_worker),
            trigger=CronTrigger(minute="*/1"),
            id="reminder_poll",
            replace_existing=True,
            misfire_grace_time=300,  # 5 minutes
        )
        self._scheduler.start()
        self._running = True

    def stop(self) -> None:
        if self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False

    def start_pomodoro_timer(self, duration_minutes: int = 25) -> str:
        """Add one-shot midpoint + end jobs. Returns base job_id prefix."""
        from zeno.scheduler.jobs import pomodoro_midpoint, pomodoro_end
        now = datetime.now()
        mid = now + timedelta(minutes=duration_minutes / 2)
        end = now + timedelta(minutes=duration_minutes)
        job_id = f"pomodoro_{int(now.timestamp())}"

        self._scheduler.add_job(
            functools.partial(pomodoro_midpoint, self._tts_worker, duration_minutes),
            trigger=DateTrigger(run_date=mid),
            id=f"{job_id}_mid",
        )
        self._scheduler.add_job(
            functools.partial(pomodoro_end, self._tts_worker, duration_minutes),
            trigger=DateTrigger(run_date=end),
            id=f"{job_id}_end",
        )
        return job_id

    def add_reminder(self, reminder_id: int, message: str, run_at: datetime) -> None:
        """Add a single dynamic reminder job (called when a reminder is created)."""
        from zeno.scheduler.jobs import fire_due_reminders
        # Fire a targeted one-shot rather than waiting for polling
        self._scheduler.add_job(
            functools.partial(fire_due_reminders, self._db_path, self._tts_worker),
            trigger=DateTrigger(run_date=run_at),
            id=f"reminder_{reminder_id}",
            misfire_grace_time=300,
            replace_existing=True,
        )

    @property
    def running(self) -> bool:
        return self._running
