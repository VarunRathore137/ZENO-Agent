import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import SystemBar from './components/SystemBar';
import Dashboard from './components/Dashboard';
import BriefingPanel from './components/BriefingPanel';
import Settings from './components/Settings';
import Overlay from './components/Overlay';
import SudoPopup, { SudoRequest } from './components/SudoPopup';
import ToastContainer, { ToastItem } from './components/Toast';
import { useDaemonWs } from './hooks/useDaemonWs';
import type { ZenoState } from './components/ArcReactor';
import './index.css';

type View = 'dashboard' | 'briefing' | 'tasks' | 'settings';
const isOverlay = window.location.hash === '#/overlay';

export default function App() {
  const [view, setView]           = useState<View>('dashboard');
  const [apiBase, setApiBase]     = useState('http://127.0.0.1:8766');
  const [zenoState, setZenoState] = useState<ZenoState>('idle');
  const [sudoRequests, setSudoRequests] = useState<SudoRequest[]>([]);
  const [toasts, setToasts]       = useState<ToastItem[]>([]);

  // Show the Tauri window as soon as React has mounted.
  useEffect(() => {
    import('@tauri-apps/api/window')
      .then(({ getCurrentWindow }) => getCurrentWindow().show())
      .catch(() => {}); // not running inside Tauri — ignore
  }, []);

  // Resolve API base from Tauri
  useEffect(() => {
    if (!isOverlay) {
      invoke<string>('get_api_base').then(setApiBase).catch(() => {});
    }
  }, []);

  // Listen for daemon_state events from Tauri tray actions (focus/mute toggles)
  useEffect(() => {
    if (isOverlay) return;
    const unlisten = listen<Record<string, unknown>>('daemon_state', (ev) => {
      console.log('[ZENO] daemon_state:', ev.payload);
    });
    return () => { unlisten.then(f => f()); };
  }, []);

  // WebSocket real-time events from Python daemon
  useDaemonWs((msg) => {
    if (msg.type === 'overlay_show') {
      invoke('show_overlay_window').catch(console.error);
    }
    if (msg.type === 'zeno_state') {
      setZenoState((msg.state as ZenoState) ?? 'idle');
    }
    if (msg.type === 'tts_active') {
      setZenoState(Boolean(msg.active) ? 'speaking' : 'idle');
    }
    if (msg.type === 'sudo_request') {
      const req: SudoRequest = {
        id: String(msg.id),
        command: String(msg.command || ''),
        expires_in: Number(msg.expires_in || 60),
      };
      setSudoRequests(prev => [...prev.filter(r => r.id !== req.id), req]);
    }
    if (msg.type === 'reminder_fire') {
      const toast: ToastItem = {
        id: String(msg.id || Date.now()),
        message: String(msg.message || ''),
        title: msg.title ? String(msg.title) : 'REMINDER',
        type: (msg.toast_type as any) || 'reminder',
      };
      setToasts(prev => [...prev, toast]);
      // Auto-dismiss after 8 seconds
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== toast.id));
      }, 8000);
    }
  });

  const handleDismissToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  const handleHandledSudo = (id: string) => {
    setSudoRequests(prev => prev.filter(r => r.id !== id));
  };

  if (isOverlay) return <Overlay />;

  const navItems = [
    { id: 'dashboard' as View, label: 'DASHBOARD' },
    { id: 'briefing'  as View, label: 'BRIEFING' },
    { id: 'tasks'     as View, label: 'TASKS' },
    { id: 'settings'  as View, label: 'SETTINGS' },
  ];

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="logo">ZENO</div>
        <div className="logo-sub">J.A.R.V.I.S. v1.0</div>
        {navItems.map(({ id, label }) => (
          <button key={id} id={`nav-${id}`}
            className={`nav-btn ${view === id ? 'active' : ''}`}
            onClick={() => setView(id)}>
            <span className="nav-indicator" />
            {label}
          </button>
        ))}
      </nav>

      <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', flex: 1 }}>
        <SystemBar apiBase={apiBase} />
        <main className="main-content" style={{ flex: 1, overflow: 'hidden' }}>
          {view === 'dashboard' && <Dashboard apiBase={apiBase} zenoState={zenoState} />}
          {view === 'briefing'  && <BriefingPanel apiBase={apiBase} />}
          {view === 'tasks'     && (
            <div id="tasks-view" style={{ padding: '16px 20px' }}>
              <div className="panel-title" style={{ marginBottom: 16 }}>FULL TASK LIST</div>
              <p style={{ fontFamily: 'var(--font-mono)', fontSize: 10,
                color: 'var(--text-muted)', letterSpacing: 1 }}>
                USE VOICE: "HEY ZENO, SHOW MY TASKS"
              </p>
            </div>
          )}
          {view === 'settings'  && <Settings apiBase={apiBase} />}
        </main>
      </div>

      {/* Floating Notification & Authorization Layers */}
      <SudoPopup
        apiBase={apiBase}
        requests={sudoRequests}
        onHandled={handleHandledSudo}
      />
      <ToastContainer
        toasts={toasts}
        onDismiss={handleDismissToast}
      />
    </div>
  );
}
