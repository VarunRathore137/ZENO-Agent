import { useState, useRef, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { getCurrentWindow } from '@tauri-apps/api/window';

export default function Overlay() {
  const [text, setText]     = useState('');
  const [status, setStatus] = useState<'idle'|'saving'|'saved'|'error'>('idle');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const save = async () => {
    if (!text.trim() || status === 'saving') return;
    setStatus('saving');
    try {
      const apiBase = await invoke<string>('get_api_base');
      const r = await fetch(`${apiBase}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim(), source: 'overlay' }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setStatus('saved');
      setText('');
      setTimeout(() => getCurrentWindow().hide(), 500);
    } catch (e) {
      setStatus('error');
      console.error(e);
    }
  };

  const onKey = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') save();
    if (e.key === 'Escape') getCurrentWindow().hide();
  };

  return (
    <div id="overlay-root" style={{
      height: '100vh', padding: 14, display: 'flex', flexDirection: 'column', gap: 8,
      background: '#080d18', border: '1px solid rgba(0,212,255,0.5)',
      borderRadius: 8, boxSizing: 'border-box',
      boxShadow: '0 0 32px rgba(0,212,255,0.15)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontFamily: 'var(--font-hud)', fontSize: 10, letterSpacing: 3,
          color: '#00d4ff', textShadow: '0 0 8px #00d4ff' }}>⚡ QUICK CAPTURE</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9,
          color: 'rgba(200,230,255,0.3)' }}>CTRL+ENTER SAVE · ESC CLOSE</span>
      </div>

      <textarea
        ref={inputRef}
        id="overlay-input"
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={onKey}
        placeholder="Capture a thought, task, or note…"
        style={{
          flex: 1, resize: 'none', outline: 'none',
          background: 'rgba(0,212,255,0.04)', border: '1px solid rgba(0,212,255,0.2)',
          borderRadius: 4, padding: '8px 10px',
          fontFamily: 'Share Tech Mono, monospace', fontSize: 12,
          color: '#c8e6ff', lineHeight: 1.6,
        }}
      />

      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 8 }}>
        {status === 'saved' && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10,
          color: 'var(--green)' }}>✓ CAPTURED</span>}
        {status === 'error' && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10,
          color: 'var(--red)' }}>✗ FAILED</span>}
        <button
          id="overlay-save-btn"
          className="hud-btn primary"
          onClick={save}
          disabled={!text.trim() || status === 'saving'}
        >
          {status === 'saving' ? 'SAVING…' : 'SAVE'}
        </button>
      </div>
    </div>
  );
}
