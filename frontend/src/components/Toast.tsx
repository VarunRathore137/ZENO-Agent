import React from 'react';
import { Bell, Info, AlertTriangle, X } from 'lucide-react';

export interface ToastItem {
  id: string;
  message: string;
  title?: string;
  type?: 'reminder' | 'info' | 'warning';
  duration?: number;
}

interface Props {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

export default function ToastContainer({ toasts, onDismiss }: Props) {
  if (toasts.length === 0) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: 24,
      right: 24,
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      maxWidth: 360,
      pointerEvents: 'none',
    }}>
      {toasts.map(toast => {
        const isReminder = toast.type === 'reminder' || !toast.type;
        const isWarning = toast.type === 'warning';
        const borderColor = isWarning ? 'var(--orange)' : isReminder ? 'var(--cyan)' : 'var(--border-glow)';
        const glow = isWarning ? 'var(--orange-glow)' : 'var(--cyan-glow)';
        const Icon = isWarning ? AlertTriangle : isReminder ? Bell : Info;

        return (
          <div
            key={toast.id}
            style={{
              pointerEvents: 'auto',
              background: '#080d18',
              border: `1px solid ${borderColor}`,
              boxShadow: `0 0 20px rgba(0, 0, 0, 0.6), ${glow}`,
              borderRadius: 'var(--radius-md)',
              padding: '12px 14px',
              display: 'flex',
              gap: 12,
              alignItems: 'flex-start',
              animation: 'toast-slide-in 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          >
            <div style={{
              background: isWarning ? 'rgba(255, 107, 53, 0.15)' : 'rgba(0, 212, 255, 0.15)',
              borderRadius: 'var(--radius-sm)',
              padding: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isWarning ? 'var(--orange)' : 'var(--cyan)',
            }}>
              <Icon size={16} />
            </div>

            <div style={{ flex: 1 }}>
              <div style={{
                fontFamily: 'var(--font-hud)',
                fontSize: 10,
                letterSpacing: 2,
                color: isWarning ? 'var(--orange)' : 'var(--cyan)',
                marginBottom: 2,
                fontWeight: 700,
              }}>
                {toast.title || (isReminder ? 'REMINDER' : 'SYSTEM NOTIFICATION')}
              </div>
              <div style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--text-primary)',
                lineHeight: 1.4,
              }}>
                {toast.message}
              </div>
            </div>

            <button
              onClick={() => onDismiss(toast.id)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
