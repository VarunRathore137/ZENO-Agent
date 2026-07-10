import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import SystemBar from './components/SystemBar';
import Dashboard from './components/Dashboard';
import BriefingPanel from './components/BriefingPanel';
import Settings from './components/Settings';
import Overlay from './components/Overlay';
import { useDaemonWs } from './hooks/useDaemonWs';
import './index.css';

type View = 'dashboard' | 'briefing' | 'tasks' | 'settings';
const isOverlay = window.location.hash === '#/overlay';

export default function App() {
  const [view, setView]         = useState<View>('dashboard');
  const [apiBase, setApiBase]   = useState('http://127.0.0.1:8766');
  const [ttsActive, setTtsActive] = useState(false);

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
      // Re-poll /system automatically; nothing specific needed here
      console.log('[ZENO] daemon_state:', ev.payload);
    });
    return () => { unlisten.then(f => f()); };
  }, []);

  // WebSocket real-time events from Python daemon
  useDaemonWs((msg) => {
    if (msg.type === 'overlay_show') {
      // Python daemon sent overlay trigger — show overlay window via Tauri
      invoke('show_overlay_window').catch(console.error);
    }
    if (msg.type === 'tts_active') {
      setTtsActive(Boolean(msg.active));
    }
  });

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
          {view === 'dashboard' && <Dashboard apiBase={apiBase} ttsActive={ttsActive} />}
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
    </div>
  );
}
