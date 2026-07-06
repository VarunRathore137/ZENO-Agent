from apscheduler.triggers.cron import CronTrigger

def register_static_jobs(scheduler, config: dict, db_path: str, ai_router, tts_worker) -> None:
    """Register all static (time-driven) jobs onto the scheduler instance."""
    zeno_cfg = config.get("zeno", {})

    # Parse morning_briefing_time "HH:MM"
    briefing_time = zeno_cfg.get("morning_briefing_time", "08:30")
    hour, minute = (int(x) for x in briefing_time.split(":"))

    from zeno.scheduler.jobs import (
        deliver_morning_briefing, regenerate_weekly_analytics
    )
    import functools

    # Briefing — 1 hour misfire grace
    scheduler.add_job(
        functools.partial(deliver_morning_briefing, db_path, ai_router, tts_worker),
        trigger=CronTrigger(hour=hour, minute=minute),
        id="morning_briefing",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour
    )

    # Weekly analytics — Sunday 23:00, NO misfire grace (skip if missed)
    scheduler.add_job(
        functools.partial(regenerate_weekly_analytics, db_path),
        trigger=CronTrigger(day_of_week="sun", hour=23, minute=0),
        id="weekly_analytics",
        replace_existing=True,
        misfire_grace_time=None,  # skip if missed
    )
