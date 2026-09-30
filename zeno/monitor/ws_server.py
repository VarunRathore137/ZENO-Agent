import asyncio, json, sqlite3, sys
from datetime import datetime, timezone
from zeno.monitor.privacy import is_domain_excluded

try:
    import websockets
    _WS_AVAILABLE = True
except ImportError:
    _WS_AVAILABLE = False

# PORT IS HARDCODED — if changed here, also change WS_URL in zeno/extension/background.js
# and useDaemonWs.ts in the React frontend.
# These constants must always match. Search for "8767" to find all locations.
# Port map: 8765 = OS Agent (FastAPI) | 8766 = REST API (FastAPI) | 8767 = Browser WS (this)
HOST = "localhost"
PORT = 8767


_ws_instance = None
_ws_loop = None


def broadcast_state(state: str) -> None:
    """Thread-safe broadcast of ZENO state to all connected React frontend clients."""
    if _ws_instance is None or _ws_loop is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(
            _ws_instance.broadcast({"type": "zeno_state", "state": state}),
            _ws_loop,
        )
    except Exception:
        pass


def broadcast_event(payload: dict) -> None:
    """Thread-safe broadcast of any JSON payload to all connected clients."""
    if _ws_instance is None or _ws_loop is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(
            _ws_instance.broadcast(payload),
            _ws_loop,
        )
    except Exception:
        pass


class BrowserWebSocketServer:
    """
    Listens on ws://localhost:8767 for browser extension and React frontend events.
    """
    def __init__(self, db_path: str, send_page_title: bool = True) -> None:
        self._db_path = db_path
        self._send_page_title = send_page_title   # from config.yaml browser_extension.send_page_title
        self._server = None
        # In-flight sessions: domain → session dict
        # Last open wins per domain (handles rapid tab switches gracefully)
        self._pending: dict[str, dict] = {}
        self.connected_clients: set = set()  # tracks all active WebSocket connections

    async def start(self) -> None:
        """Start the WebSocket server. Returns when server is ready to accept connections."""
        if not _WS_AVAILABLE:
            print("[WSServer] 'websockets' not installed — browser tracking disabled.", file=sys.stderr)
            return

        global _ws_instance, _ws_loop
        _ws_instance = self
        try:
            _ws_loop = asyncio.get_running_loop()
        except RuntimeError:
            _ws_loop = asyncio.get_event_loop()

        self._server = await websockets.serve(self._handle, HOST, PORT)
        print(f"[WSServer] Listening on ws://{HOST}:{PORT}")

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle(self, ws) -> None:
        """Handle one WebSocket connection (browser extension OR React frontend)."""
        self.connected_clients.add(ws)
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                msg_type = msg.get("type")
                if msg_type == "tab_open":
                    await self._on_tab_open(msg)
                elif msg_type == "tab_close":
                    await self._on_tab_close(msg)
                # ping: intentional no-op
        finally:
            self.connected_clients.discard(ws)

    async def broadcast(self, payload: dict) -> None:
        """
        Push a JSON message to ALL connected WebSocket clients
        (browser extension connections + React frontend connections).

        Called from non-async context via:
            asyncio.run_coroutine_threadsafe(ws_server.broadcast(payload), loop)
        """
        if not self.connected_clients:
            return
        message = json.dumps(payload)
        # Iterate over a snapshot to avoid mutation during iteration
        for ws in list(self.connected_clients):
            try:
                await ws.send(message)
            except Exception:
                self.connected_clients.discard(ws)

    async def _on_tab_open(self, msg: dict) -> None:
        domain = msg.get("domain", "unknown")
        # Privacy: drop excluded domains entirely — no DB write, no log
        if is_domain_excluded(domain, self._db_path):
            return

        # Privacy: strip page_title if domain-only mode enabled in config
        page_title = msg.get("page_title", "") if self._send_page_title else ""

        # Privacy: redact page_title if it matches window_title_pattern exclusions
        # Reuse the window_title matching path by passing page_title as window_title
        from zeno.monitor.privacy import is_excluded
        if page_title and is_excluded("", page_title, self._db_path):
            page_title = "[redacted]"

        self._pending[domain] = {
            "browser":      msg.get("browser", "chrome"),
            "domain":       domain,
            "page_title":   page_title,
            "url_category": msg.get("url_category", "unknown"),
            "started_at":   msg.get("started_at", datetime.now(timezone.utc).isoformat()),
        }

    async def _on_tab_close(self, msg: dict) -> None:
        domain = msg.get("domain", "")
        session = self._pending.pop(domain, None)
        if session is None:
            return  # no matching open session — ignore orphan close

        ended_at = datetime.now(timezone.utc).isoformat()
        dwell_seconds = int(msg.get("dwell_seconds", 0))

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._write_session, session, ended_at, dwell_seconds
            )
        except Exception as e:
            print(f"[WSServer] DB write error: {e}", file=sys.stderr)

    def _write_session(self, session: dict, ended_at: str, dwell_seconds: int) -> None:
        """Blocking DB write — called via run_in_executor, not on event loop."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO browser_sessions "
                "(browser, domain, page_title, url_category, started_at, ended_at, dwell_seconds) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session["browser"],
                    session["domain"],
                    session["page_title"],
                    session["url_category"],
                    session["started_at"],
                    ended_at,
                    dwell_seconds,
                )
            )
