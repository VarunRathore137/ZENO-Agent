import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import './index.css';

type View = 'dashboard' | 'briefing' | 'tasks' | 'settings';
const isOverlay = window.location.hash === '#/overlay';

export default function App() {
  const [view, setView] = useState<View>('dashboard');
  const [apiBase, setApiBase] = useState('http://127.0.0.1:8766');

  useEffect(() => {
    if (!isOverlay) {
      invoke<string>('get_api_base').then(setApiBase).catch(() => {});
    }
  }, []);

  if (isOverlay) {
    return (
      <div style={{padding:16,background:'#050810',height:'100vh',
        border:'1px solid #00d4ff',borderRadius:8,boxSizing:'border-box'}}>
        <p style={{color:'#00d4ff',fontFamily:'Share Tech Mono, monospace',fontSize:13}}>
          ⚡ ZENO — Quick Capture (Plan 9.3)
        </p>
      </div>
    );
  }

  const navItems = [
    {id:'dashboard' as View, label:'DASHBOARD'},
    {id:'briefing'  as View, label:'BRIEFING'},
    {id:'tasks'     as View, label:'TASKS'},
    {id:'settings'  as View, label:'SETTINGS'},
  ];

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="logo">ZENO</div>
        <div className="logo-sub">J.A.R.V.I.S. v1.0</div>
        {navItems.map(({id, label}) => (
          <button key={id} id={`nav-${id}`}
            className={`nav-btn ${view===id?'active':''}`}
            onClick={() => setView(id)}>
            <span className="nav-indicator" />
            {label}
          </button>
        ))}
      </nav>
      <main className="main-content">
        <div style={{color:'#00d4ff',fontFamily:'Share Tech Mono',padding:32}}>
          {view.toUpperCase()} view — components wired in Plan 9.3
          <br/>API: {apiBase}
        </div>
      </main>
    </div>
  );
}
