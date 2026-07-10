import { useApi } from '../hooks/useApi';

interface SystemData {
  cpu_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  ram_percent: number;
  battery_percent: number | null;
  battery_plugged: boolean | null;
  gpu_percent: number | null;
  net_bytes_sent: number;
  net_bytes_recv: number;
  focus_mode: boolean;
  tts_muted: boolean;
}

interface Props { apiBase: string; }

function colorClass(pct: number): string {
  if (pct >= 85) return 'crit';
  if (pct >= 65) return 'warn';
  return 'ok';
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${bytes}B`;
}

export default function SystemBar({ apiBase }: Props) {
  const { data } = useApi<SystemData>(`${apiBase}/system`, 3000);

  if (!data) {
    return (
      <div className="hud-bar" id="hud-bar">
        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 10 }}>
          CONNECTING TO DAEMON…
        </span>
      </div>
    );
  }

  const stats = [
    { label: 'CPU',     value: `${data.cpu_percent.toFixed(0)}%`,              cls: colorClass(data.cpu_percent) },
    { label: 'GPU',     value: data.gpu_percent != null ? `${data.gpu_percent}%` : 'N/A', cls: data.gpu_percent != null ? colorClass(data.gpu_percent) : '' },
    { label: 'RAM',     value: `${data.ram_used_gb}/${data.ram_total_gb}GB`,    cls: colorClass(data.ram_percent) },
    { label: 'BAT',     value: data.battery_percent != null ? `${data.battery_percent}%${data.battery_plugged ? '⚡' : ''}` : 'N/A', cls: data.battery_percent != null ? colorClass(100 - data.battery_percent) : '' },
    { label: '↑NET',    value: formatBytes(data.net_bytes_sent),                cls: '' },
    { label: '↓NET',    value: formatBytes(data.net_bytes_recv),                cls: 'ok' },
  ];

  return (
    <div className="hud-bar" id="hud-bar">
      {stats.map((s, i) => (
        <span key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <span className="hud-stat">
            <span style={{ color: 'var(--text-muted)', letterSpacing: 1 }}>{s.label}</span>
            <span className={`hud-stat-value ${s.cls}`} id={`sys-${s.label.toLowerCase().replace(/[^a-z]/g,'')}`}>
              {s.value}
            </span>
          </span>
          {i < stats.length - 1 && <span className="hud-divider" />}
        </span>
      ))}
      {data.focus_mode && (
        <span style={{ marginLeft: 'auto', color: 'var(--orange)', fontFamily: 'var(--font-hud)',
          fontSize: 9, letterSpacing: 2, textShadow: 'var(--orange-glow)' }}>
          ◈ FOCUS MODE
        </span>
      )}
      {data.tts_muted && (
        <span style={{ marginLeft: data.focus_mode ? 12 : 'auto', color: 'var(--red)',
          fontFamily: 'var(--font-hud)', fontSize: 9, letterSpacing: 2 }}>
          ⊘ VOICE MUTED
        </span>
      )}
    </div>
  );
}
