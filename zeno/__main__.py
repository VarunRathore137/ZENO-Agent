# zeno/__main__.py
from zeno.logging_setup import configure_logging
import os
configure_logging(debug=os.environ.get("ZENO_DEBUG", "").lower() in ("1", "true"))

import asyncio
import threading
import logging
from pathlib import Path

from zeno.api.server import ZenoDaemonAPI
from zeno.monitor.ws_server import BrowserWebSocketServer
from zeno.voice.hotkeys import create_listener

"""ZENO entry point."""

logger = logging.getLogger(__name__)

async def run_daemon() -> None:
    db_path = str(Path.home() / "Zeno" / "Zeno.db")
    
    # 1. Start FastAPI background thread (port 8766)
    stop_event = threading.Event()
    api = ZenoDaemonAPI(db_path=db_path, stop_event=stop_event)
    api.start()

    # 2. Start WebSocket Server for IPC/Browser Extension (port 8765)
    ws = BrowserWebSocketServer(db_path=db_path, send_page_title=True)
    await ws.start()

    # 3. Start Global Hotkeys (Ctrl+Shift+Space for overlay)
    loop = asyncio.get_running_loop()
    hotkeys = create_listener(ws_server=ws, event_loop=loop)
    hotkeys.start()

    logger.info("ZENO Daemon fully started.")
    print("ZENO is running and listening on localhost:8765 and localhost:8766. Press Ctrl+C to stop.")

    # Block until shutdown requested
    while not stop_event.is_set():
        await asyncio.sleep(1.0)
        
    await ws.stop()
    hotkeys.stop()
    logger.info("ZENO Daemon shutdown complete.")


def main() -> None:
    """Start the ZENO assistant daemon."""
    print("ZENO daemon initializing...")
    try:
        asyncio.run(run_daemon())
    except KeyboardInterrupt:
        print("\nShutting down due to KeyboardInterrupt...")

if __name__ == "__main__":
    main()
