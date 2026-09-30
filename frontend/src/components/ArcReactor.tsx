export type ZenoState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface Props {
  state?: ZenoState;  // default: 'idle'
  size?: number;      // diameter in px (default 180)
}

const STATE_CONFIG: Record<ZenoState, {
  label: string;
  outerColor: string;
  midColor: string;
  innerColor: string;
  coreColor: string;
  dotColor: string;
  glowColor: string;
  cssClass: string;
}> = {
  idle: {
    label: '◈ STANDBY',
    outerColor: 'rgba(0,212,255,0.08)',
    midColor: '#00d4ff',
    innerColor: 'rgba(124,58,237,0.7)',
    coreColor: 'rgba(0,212,255,0.08)',
    dotColor: '#00d4ff',
    glowColor: 'rgba(0,212,255,0.4)',
    cssClass: '',
  },
  listening: {
    label: '◉ LISTENING',
    outerColor: 'rgba(0,212,255,0.15)',
    midColor: '#00d4ff',
    innerColor: 'rgba(0,212,255,0.9)',
    coreColor: 'rgba(0,212,255,0.15)',
    dotColor: '#00d4ff',
    glowColor: 'rgba(0,212,255,0.8)',
    cssClass: 'arc-listening',
  },
  thinking: {
    label: '⟳ PROCESSING',
    outerColor: 'rgba(124,58,237,0.12)',
    midColor: '#7c3aed',
    innerColor: 'rgba(124,58,237,0.9)',
    coreColor: 'rgba(124,58,237,0.12)',
    dotColor: '#a855f7',
    glowColor: 'rgba(124,58,237,0.7)',
    cssClass: 'arc-thinking',
  },
  speaking: {
    label: '▶ SPEAKING',
    outerColor: 'rgba(0,255,136,0.12)',
    midColor: '#00ff88',
    innerColor: 'rgba(0,255,136,0.7)',
    coreColor: 'rgba(0,255,136,0.12)',
    dotColor: '#00ff88',
    glowColor: 'rgba(0,255,136,0.7)',
    cssClass: 'arc-speaking',
  },
};

export default function ArcReactor({ state = 'idle', size = 180 }: Props) {
  const r = size / 2;
  const cx = r, cy = r;
  const cfg = STATE_CONFIG[state];

  // Generate tick marks on the outer ring
  const ticks = Array.from({ length: 48 }, (_, i) => {
    const angle = (i * 360) / 48;
    const rad = (angle * Math.PI) / 180;
    const r1 = r - 4, r2 = i % 4 === 0 ? r - 14 : r - 8;
    return {
      x1: cx + r1 * Math.cos(rad), y1: cy + r1 * Math.sin(rad),
      x2: cx + r2 * Math.cos(rad), y2: cy + r2 * Math.sin(rad),
      major: i % 4 === 0,
    };
  });

  const majorTickColor = state === 'thinking' ? 'rgba(124,58,237,0.6)'
    : state === 'speaking' ? 'rgba(0,255,136,0.6)'
    : 'rgba(0,212,255,0.6)';
  const minorTickColor = state === 'thinking' ? 'rgba(124,58,237,0.2)'
    : state === 'speaking' ? 'rgba(0,255,136,0.2)'
    : 'rgba(0,212,255,0.2)';

  return (
    <div className={`arc-reactor ${cfg.cssClass}`} id="arc-reactor">
      <div className="arc-ring" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Outer glow ring */}
          <circle cx={cx} cy={cy} r={r - 2} fill="none"
            stroke={cfg.outerColor} strokeWidth={1} />

          {/* Tick marks (static) */}
          {ticks.map((t, i) => (
            <line key={i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2}
              stroke={t.major ? majorTickColor : minorTickColor}
              strokeWidth={t.major ? 1.5 : 0.8} />
          ))}

          {/* Rotating dashed arc */}
          <g className="arc-ring-rotate">
            <circle cx={cx} cy={cy} r={r - 18} fill="none"
              stroke={cfg.midColor} strokeWidth={1.5} strokeOpacity={0.5}
              strokeDasharray="12 6" />
          </g>

          {/* Pulsing middle ring */}
          <circle cx={cx} cy={cy} r={r - 32} fill="none"
            className="arc-ring-pulse"
            stroke={cfg.midColor} strokeWidth={2} strokeOpacity={0.8}
            strokeDasharray="40 8" />

          {/* Counter-rotating inner arc */}
          <g style={{ transformOrigin: `${cx}px ${cy}px`,
            animation: 'arc-spin 5s linear infinite reverse' }}>
            <circle cx={cx} cy={cy} r={r - 48} fill="none"
              stroke={cfg.innerColor} strokeWidth={1.5}
              strokeDasharray="20 10" />
          </g>

          {/* Inner glow core */}
          <circle cx={cx} cy={cy} r={r - 62} fill="none"
            stroke={cfg.midColor} strokeWidth={1} strokeOpacity={0.3} />

          {/* Core fill */}
          <circle cx={cx} cy={cy} r={r - 70}
            fill={cfg.coreColor} />
          <circle cx={cx} cy={cy} r={r - 76}
            fill={cfg.coreColor}
            className="arc-ring-pulse" />

          {/* Center dot */}
          <circle cx={cx} cy={cy} r={4}
            fill={cfg.dotColor}
            filter="url(#glow)" />

          {/* SVG glow filter */}
          <defs>
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
        </svg>
      </div>

      <div className={`arc-status arc-status-${state}`} id="arc-status">
        {cfg.label}
      </div>
    </div>
  );
}
