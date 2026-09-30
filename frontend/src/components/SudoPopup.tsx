import React, { useState, useEffect } from 'react';
import { ShieldAlert, Check, X, Clock, Terminal } from 'lucide-react';

export interface SudoRequest {
  id: string;
  command: string;
  expires_in?: number;
}

interface Props {
  apiBase: string;
  requests: SudoRequest[];
  onHandled: (id: string) => void;
}

export default function SudoPopup({ apiBase, requests, onHandled }: Props) {
  const current = requests[0];
  const [timeLeft, setTimeLeft] = useState<number>(60);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!current) return;
    const initialTime = current.expires_in || 60;
    setTimeLeft(initialTime);

    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          onHandled(current.id);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [current?.id]);

  if (!current) return null;

  const handleAction = async (action: 'approve' | 'reject') => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await fetch(`${apiBase}/api/sudo/confirm/${current.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
    } catch (e) {
      console.error('Failed to submit sudo confirmation:', e);
    } finally {
      setSubmitting(false);
      onHandled(current.id);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 10000,
      background: 'rgba(5, 8, 16, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 16,
    }}>
      <div style={{
        background: '#080d18',
        border: '1px solid var(--red)',
        boxShadow: '0 0 50px rgba(255, 43, 74, 0.3)',
        borderRadius: 'var(--radius-md)',
        maxWidth: 480,
        width: '100%',
        overflow: 'hidden',
        animation: 'toast-slide-in 0.25s ease-out',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          background: 'rgba(255, 43, 74, 0.08)',
          borderBottom: '1px solid rgba(255, 43, 74, 0.25)',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}>
          <div style={{
            background: 'rgba(255, 43, 74, 0.2)',
            borderRadius: 'var(--radius-sm)',
            padding: 6,
            color: 'var(--red)',
          }}>
            <ShieldAlert size={20} />
          </div>
          <div>
            <div style={{
              fontFamily: 'var(--font-hud)',
              fontSize: 12,
              letterSpacing: 2,
              color: 'var(--red)',
              fontWeight: 700,
            }}>
              ELEVATED PRIVILEGE AUTHORIZATION
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              color: 'var(--text-muted)',
            }}>
              A terminal command requires administrative confirmation
            </div>
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Command preview */}
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              color: 'var(--text-muted)',
              marginBottom: 6,
              letterSpacing: 1,
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}>
              <Terminal size={12} /> COMMAND TO EXECUTE:
            </div>
            <div style={{
              background: '#050810',
              border: '1px solid var(--border-dim)',
              borderRadius: 'var(--radius-sm)',
              padding: '10px 12px',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              color: '#fff',
              wordBreak: 'break-all',
            }}>
              {current.command}
            </div>
          </div>

          {/* Expiry countdown */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            color: 'var(--orange)',
          }}>
            <Clock size={13} />
            <span>AUTHORIZATION EXPIRES IN: <strong>{timeLeft}s</strong></span>
          </div>

          {/* Security alert text */}
          <div style={{
            background: 'rgba(255, 43, 74, 0.05)',
            border: '1px solid rgba(255, 43, 74, 0.15)',
            borderRadius: 'var(--radius-sm)',
            padding: '8px 12px',
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'rgba(255, 200, 200, 0.8)',
            lineHeight: 1.4,
          }}>
            WARNING: Elevated commands can alter system files, install software, or modify security settings. Approve only if you requested this command.
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
            <button
              onClick={() => handleAction('reject')}
              disabled={submitting}
              className="hud-btn"
              style={{
                flex: 1,
                padding: '10px',
                borderColor: 'rgba(255, 43, 74, 0.5)',
                color: 'var(--red)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <X size={14} /> REJECT
            </button>

            <button
              onClick={() => handleAction('approve')}
              disabled={submitting}
              className="hud-btn primary"
              style={{
                flex: 1,
                padding: '10px',
                background: 'rgba(0, 255, 136, 0.15)',
                borderColor: 'var(--green)',
                color: 'var(--green)',
                boxShadow: '0 0 16px rgba(0, 255, 136, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <Check size={14} /> AUTHORIZE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
