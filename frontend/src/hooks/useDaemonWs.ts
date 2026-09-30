import { useEffect, useRef, useCallback } from 'react';

type Handler = (msg: Record<string, unknown>) => void;

export function useDaemonWs(onMessage: Handler) {
  const wsRef = useRef<WebSocket | null>(null);
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  const connect = useCallback(() => {
    // Don't connect in overlay window — it doesn't need the WS
    if (window.location.hash === '#/overlay') return;

    // Port 8767 = BrowserWebSocket (Python daemon)
    // Port 8765 = OS Agent (FastAPI) — different service, don't connect here
    const ws = new WebSocket('ws://localhost:8767');
    wsRef.current = ws;

    ws.onopen = () => {
      // Send ping to register as a client
      ws.send(JSON.stringify({ type: 'ping' }));
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        handlerRef.current(msg);
      } catch { /* ignore malformed */ }
    };

    ws.onclose = () => {
      // Reconnect after 3s (daemon may not be running yet on startup)
      setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => { wsRef.current?.close(); };
  }, [connect]);
}
