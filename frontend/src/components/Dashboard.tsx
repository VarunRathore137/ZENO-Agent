import { useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Legend,
} from 'recharts';
import ArcReactor from './ArcReactor';
import type { ZenoState } from './ArcReactor';
import CharacterVisualizer from './CharacterVisualizer';
import { useApi } from '../hooks/useApi';

interface AnalyticsRow {
  day: string;
  deep_work_minutes: number;
  distraction_minutes: number;
  idle_minutes: number;
}

interface TaskRow {
  id: number; title: string; priority: number;
  status: string; due_date: string | null;
}

interface SystemData {
  cpu_percent: number; ram_used_gb: number; ram_total_gb: number;
  ram_percent: number; battery_percent: number | null;
  gpu_percent: number | null;
}

interface Props { apiBase: string; zenoState: ZenoState; }

const TOOLTIP_STYLE = {
  background: '#080d18', border: '1px solid rgba(0,212,255,0.3)',
  borderRadius: 6, color: '#c8e6ff', fontSize: 11,
  fontFamily: 'Share Tech Mono, monospace',
};

export default function Dashboard({ apiBase, zenoState }: Props) {
  const { data: analytics } = useApi<{ analytics: AnalyticsRow[] }>(`${apiBase}/analytics`, 60000);
  const { data: tasksData }  = useApi<{ tasks: TaskRow[] }>(`${apiBase}/tasks`, 30000);
  const { data: sysData }    = useApi<SystemData>(`${apiBase}/system`, 5000);

  const [visualMode, setVisualMode] = useState<'reactor' | 'character'>(() => {
    return (localStorage.getItem('zeno_visual_mode') as 'reactor' | 'character') || 'reactor';
  });

  const toggleVisualMode = (mode: 'reactor' | 'character') => {
    setVisualMode(mode);
    localStorage.setItem('zeno_visual_mode', mode);
  };

  const rows = analytics?.analytics ?? [];
  const tasks = tasksData?.tasks ?? [];

  // System gauge data
  const gauges = [
    { label: 'CPU', pct: sysData?.cpu_percent ?? 0 },
    { label: 'RAM', pct: sysData?.ram_percent ?? 0 },
    { label: 'GPU', pct: sysData?.gpu_percent ?? 0 },
  ].filter(g => g.pct > 0 || g.label !== 'GPU');

  const gaugeClass = (pct: number) => pct >= 85 ? 'crit' : pct >= 65 ? 'warn' : '';

  const priorityClass = (p: number) => p >= 3 ? 'p3' : p === 2 ? 'p2' : p === 1 ? 'p1' : 'p0';

  return (
    <div id="dashboard-view" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Top section: Arc reactor + System gauges */}
      <div style={{ display: 'grid', gridTemplateColumns: visualMode === 'character' ? '280px 1fr' : '240px 1fr', gap: 16, padding: '16px 20px 0', transition: 'grid-template-columns 0.3s ease' }}>

        {/* Visual Core: Arc Reactor or Character Avatar */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="panel-title">CORE STATUS</span>
            <div style={{ display: 'flex', gap: 4 }}>
              <button
                className={`hud-btn ${visualMode === 'reactor' ? 'primary' : ''}`}
                style={{ fontSize: 8, padding: '2px 7px' }}
                onClick={() => toggleVisualMode('reactor')}
                title="Switch to Arc Reactor"
              >
                REACTOR
              </button>
              <button
                className={`hud-btn ${visualMode === 'character' ? 'primary' : ''}`}
                style={{ fontSize: 8, padding: '2px 7px' }}
                onClick={() => toggleVisualMode('character')}
                title="Switch to Persona Avatar"
              >
                AVATAR
              </button>
            </div>
          </div>
          {visualMode === 'reactor' ? (
            <ArcReactor state={zenoState} size={160} />
          ) : (
            <CharacterVisualizer state={zenoState} onSwitchToReactor={() => toggleVisualMode('reactor')} />
          )}
        </div>

        {/* System gauges */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">SYSTEM METRICS</span>
          </div>
          <div className="panel-body">
            {sysData ? (
              <>
                {gauges.map(g => (
                  <div key={g.label} className="gauge-row">
                    <span className="gauge-label">{g.label}</span>
                    <div className="gauge-track">
                      <div className={`gauge-fill ${gaugeClass(g.pct)}`}
                        style={{ width: `${g.pct}%` }} />
                    </div>
                    <span className="gauge-val">{g.pct.toFixed(0)}%</span>
                  </div>
                ))}
                {sysData.battery_percent != null && (
                  <div className="gauge-row">
                    <span className="gauge-label">BAT</span>
                    <div className="gauge-track">
                      <div className={`gauge-fill ${gaugeClass(100 - sysData.battery_percent)}`}
                        style={{ width: `${sysData.battery_percent}%` }} />
                    </div>
                    <span className="gauge-val">{sysData.battery_percent}%</span>
                  </div>
                )}
                <div style={{ marginTop: 12, fontFamily: 'var(--font-mono)', fontSize: 10,
                  color: 'var(--text-muted)', letterSpacing: 1 }}>
                  RAM: {sysData.ram_used_gb}GB / {sysData.ram_total_gb}GB
                </div>
              </>
            ) : (
              <div className="hud-loading">AWAITING DAEMON…</div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom section: Chart + Tasks */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 16,
        padding: '16px 20px', flex: 1, overflow: 'hidden' }}>

        {/* 7-day analytics chart */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">7-DAY ACTIVITY</span>
          </div>
          <div className="panel-body" style={{ height: 'calc(100% - 44px)' }}>
            {rows.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%" id="analytics-chart">
                <AreaChart data={rows} margin={{ top: 4, right: 12, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="deepGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#00d4ff" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="distGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#ff6b35" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ff6b35" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="2 4" stroke="rgba(0,212,255,0.07)" />
                  <XAxis dataKey="day" tick={{ fill: 'rgba(200,230,255,0.4)', fontSize: 10,
                    fontFamily: 'Share Tech Mono' }}
                    tickFormatter={d => d.slice(5)} />
                  <YAxis tick={{ fill: 'rgba(200,230,255,0.4)', fontSize: 10,
                    fontFamily: 'Share Tech Mono' }} unit="h" />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'Share Tech Mono',
                    color: 'rgba(200,230,255,0.5)' }} />
                  <Area type="monotone" dataKey="deep_work_minutes" name="Deep Work"
                    stroke="#00d4ff" strokeWidth={2} fill="url(#deepGrad)" />
                  <Area type="monotone" dataKey="distraction_minutes" name="Distraction"
                    stroke="#ff6b35" strokeWidth={1.5} fill="url(#distGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="hud-loading">NO ACTIVITY DATA</div>
            )}
          </div>
        </div>

        {/* Today's tasks */}
        <div className="panel" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div className="panel-header">
            <span className="panel-title">TODAY'S TASKS</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10,
              color: 'var(--text-muted)' }}>{tasks.length} ITEMS</span>
          </div>
          <div className="panel-body" style={{ overflowY: 'auto', flex: 1 }} id="task-list">
            {tasks.length === 0 ? (
              <div className="hud-loading">NO TASKS TODAY</div>
            ) : (
              tasks.map(t => (
                <div key={t.id} className="task-item">
                  <span className={`task-dot ${priorityClass(t.priority)}`} />
                  <span className="task-title">{t.title}</span>
                  <span className={`task-badge ${t.status}`}>{t.status}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
