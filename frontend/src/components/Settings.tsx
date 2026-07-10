import { useApi } from '../hooks/useApi';

interface SettingsData {
  user_name: string|null; wake_word: string|null; tts_engine: string|null;
  stt_model: string|null; claude_model: string|null;
  working_hours_start: string|null; working_hours_end: string|null; timezone: string|null;
}

interface Props { apiBase: string; }

const LABELS: Record<keyof SettingsData, string> = {
  user_name: 'OPERATOR', wake_word: 'WAKE WORD', tts_engine: 'TTS ENGINE',
  stt_model: 'STT MODEL', claude_model: 'LLM MODEL',
  working_hours_start: 'SHIFT START', working_hours_end: 'SHIFT END', timezone: 'TIMEZONE',
};

export default function Settings({ apiBase }: Props) {
  const { data, loading, error } = useApi<{ settings: SettingsData }>(`${apiBase}/settings`);

  return (
    <div id="settings-view" style={{ padding: '16px 20px' }}>
      <div className="panel-title" style={{ marginBottom: 20 }}>SYSTEM CONFIGURATION</div>
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)',
        marginBottom: 20, letterSpacing: 1 }}>
        READ-ONLY — USE VOICE COMMANDS TO MODIFY SETTINGS
      </p>

      {error && <div className="hud-error">{error}</div>}
      {loading && <div className="hud-loading">LOADING CONFIG…</div>}

      {data && (
        <div className="panel" style={{ maxWidth: 480 }}>
          <div className="panel-body">
            {(Object.keys(LABELS) as (keyof SettingsData)[]).map(key => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', padding: '8px 0',
                borderBottom: '1px solid var(--border-dim)' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10,
                  color: 'var(--text-muted)', letterSpacing: 2 }}>{LABELS[key]}</span>
                <span id={`setting-${key}`} style={{ fontFamily: 'var(--font-mono)',
                  fontSize: 11, color: 'var(--cyan)' }}>
                  {data.settings[key] ?? '—'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
