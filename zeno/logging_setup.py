"""
Configure rotating file logging for the ZENO daemon.

Call configure_logging() once, before any other import in __main__.py.
All modules then use logging.getLogger(__name__) as usual.
"""
import logging
import logging.handlers
import os
from pathlib import Path


def configure_logging(debug: bool = False) -> None:
    """
    Sets up:
      - RotatingFileHandler → ~/Zeno/logs/zeno.log (5MB × 3 backups)
      - StreamHandler (stderr) for errors only when not using pythonw

    After calling this, monitor logs with:
      Get-Content -Path "$env:USERPROFILE\\Zeno\\logs\\zeno.log" -Wait
    """
    log_dir = Path.home() / "Zeno" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "zeno.log"

    level = logging.DEBUG if debug else logging.INFO

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,   # 5 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    # Console handler: warnings+ (suppressed under pythonw since stderr is /dev/null)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # suppress noisy uvicorn access logs
    logging.info("ZENO daemon starting. Log: %s", log_path)
