"""Scheduler module — APScheduler integration."""
from zeno.scheduler.runner import ZenoScheduler

_scheduler: ZenoScheduler | None = None

def get_scheduler(config: dict, db_path: str, ai_router, tts_worker) -> ZenoScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ZenoScheduler(config, db_path, ai_router, tts_worker)
    return _scheduler

__all__ = ["ZenoScheduler", "get_scheduler"]
