import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import MemoryDashboard from './MemoryDashboard';

interface SettingsData {
  user_name: string | null;
  wake_word: string | null;
  tts_engine: string | null;
  stt_model: string | null;
  claude_model: string | null;
  working_hours_start: string | null;
  working_hours_end: string | null;
  timezone: string | null;
}

interface Props {
  apiBase: string;
}

const LABELS: Record<keyof SettingsData, string> = {
  user_name: 'OPERATOR',
  wake_word: 'WAKE WORD',
  tts_engine: 'TTS ENGINE',
  stt_model: 'STT MODEL',
  claude_model: 'LLM MODEL',
  working_hours_start: 'SHIFT START',
  working_hours_end: 'SHIFT END',
  timezone: 'TIMEZONE',
};

export default function Settings({ apiBase }: Props) {
  const { data, loading, error } = useApi<{ settings: SettingsData }>(`${apiBase}/settings`);
  const [visualMode, setVisualMode] = useState<'reactor' | 'character'>(() => {
    return (localStorage.getItem('zeno_visual_mode') as 'reactor' | 'character') || 'reactor';
  });

  const handleVisualModeChange = (mode: 'reactor' | 'character') => {
    setVisualMode(mode);
    localStorage.setItem('zeno_visual_mode', mode);
  };

  return (
    <div id="settings-view" style={{
      padding: '16px 20px',
      display: 'grid',
      gridTemplateColumns: '380px 1fr',
      gap: 16,
      height: '100%',
      boxSizing: 'border-box',
      overflow: 'hidden'
    }}>
      {/* Left Column: System Configuration */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div className="panel-header">
            <span className="panel-title">SYSTEM CONFIGURATION</span>
          </div>

          <div className="panel-body" style={{ flex: 1, overflowY: 'auto' }}>
            <p style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              color: 'var(--text-muted)',
              marginBottom: 16,
              letterSpacing: 1,
              lineHeight: 1.5,
            }}>
              SYSTEM CONFIGURATION READ-ONLY. MODIFY VIA ENVIRONMENT OR VOICE COMMANDS.
            </p>

            {error && <div className="hud-error">{error}</div>}
            {loading && <div className="hud-loading">SYNCING CONFIG…</div>}

            {data && (
              <div>
                {/* Visual Core Avatar / Reactor toggle */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 0',
                    borderBottom: '1px solid var(--border-dim)',
                  }}
                >
                  <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                    color: 'var(--text-muted)',
                    letterSpacing: 2,
                  }}>
                    VISUAL CORE
                  </span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button
                      className={`hud-btn ${visualMode === 'reactor' ? 'primary' : ''}`}
                      style={{ fontSize: 9, padding: '2px 8px' }}
                      onClick={() => handleVisualModeChange('reactor')}
                    >
                      ARC REACTOR
                    </button>
                    <button
                      className={`hud-btn ${visualMode === 'character' ? 'primary' : ''}`}
                      style={{ fontSize: 9, padding: '2px 8px' }}
                      onClick={() => handleVisualModeChange('character')}
                    >
                      AVATAR
                    </button>
                  </div>
                </div>

                {(Object.keys(LABELS) as (keyof SettingsData)[]).map(key => (
                  <div
                    key={key}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '10px 0',
                      borderBottom: '1px solid var(--border-dim)',
                    }}
                  >
                    <span style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 10,
                      color: 'var(--text-muted)',
                      letterSpacing: 2,
                    }}>
                      {LABELS[key]}
                    </span>
                    <span
                      id={`setting-${key}`}
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        color: 'var(--cyan)',
                      }}
                    >
                      {data.settings[key] ?? '—'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right Column: Knowledge / Memory Core */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        <MemoryDashboard apiBase={apiBase} />
      </div>
    </div>
  );
}
