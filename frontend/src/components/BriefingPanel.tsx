import { useApi } from '../hooks/useApi';

interface BriefingData { date: string; content: string; path: string; }
interface Props { apiBase: string; }

export default function BriefingPanel({ apiBase }: Props) {
  const { data, loading, error, refresh } = useApi<BriefingData>(`${apiBase}/briefing`);

  return (
    <div id="briefing-view" style={{ padding: '16px 20px', height: '100%',
      display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <span className="panel-title" style={{ flex: 1 }}>MORNING BRIEFING</span>
        {data && (
          <span id="briefing-date" style={{ fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--text-muted)', letterSpacing: 2 }}>{data.date}</span>
        )}
        <button id="briefing-refresh-btn" className="hud-btn" onClick={refresh} disabled={loading}>
          {loading ? 'LOADING' : 'REFRESH'}
        </button>
      </div>

      {error && <div className="hud-error">{error}</div>}

      <div className="panel" style={{ flex: 1, overflow: 'hidden', display: 'flex',
        flexDirection: 'column' }}>
        <div className="panel-body" style={{ overflowY: 'auto', flex: 1 }}>
          {loading ? (
            <div className="hud-loading">DECRYPTING BRIEFING…</div>
          ) : data?.content ? (
            <pre className="briefing-pre" id="briefing-content">{data.content}</pre>
          ) : (
            <div className="briefing-empty" id="briefing-empty">
              NO BRIEFING AVAILABLE<br />
              <span style={{ fontSize: 10, marginTop: 8, display: 'block' }}>
                SAY: "HEY ZENO, GENERATE MY MORNING BRIEFING"
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
