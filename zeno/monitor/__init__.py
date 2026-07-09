"""Monitor module — window detection, app tracking, and distraction analytics."""
from zeno.monitor.activity import ActivityMonitor
from zeno.monitor.ws_server import BrowserWebSocketServer

__all__ = ["ActivityMonitor", "BrowserWebSocketServer"]
