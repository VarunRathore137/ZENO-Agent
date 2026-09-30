import React, { useRef, useEffect, useState } from 'react';
import { User, Sparkles, AlertCircle, RefreshCw, Radio } from 'lucide-react';
import type { ZenoState } from './ArcReactor';

interface Props {
  state?: ZenoState;
  onSwitchToReactor?: () => void;
}

export default function CharacterVisualizer({ state = 'idle', onSwitchToReactor }: Props) {
  const idleRef = useRef<HTMLVideoElement | null>(null);
  const thinkingRef = useRef<HTMLVideoElement | null>(null);
  const talkingRef = useRef<HTMLVideoElement | null>(null);

  const [hasVideoError, setHasVideoError] = useState(false);
  const [videoLoaded, setVideoLoaded] = useState(false);

  // Sync video elements with ZENO voice state
  useEffect(() => {
    const playSafe = (video: HTMLVideoElement | null) => {
      if (!video) return;
      try {
        video.currentTime = 0;
        const p = video.play();
        if (p !== undefined) p.catch(() => {});
      } catch {}
    };

    const pauseSafe = (video: HTMLVideoElement | null) => {
      if (!video) return;
      try {
        video.pause();
      } catch {}
    };

    if (state === 'idle' || state === 'listening') {
      playSafe(idleRef.current);
      pauseSafe(thinkingRef.current);
      pauseSafe(talkingRef.current);
    } else if (state === 'thinking') {
      playSafe(thinkingRef.current);
      pauseSafe(idleRef.current);
      pauseSafe(talkingRef.current);
    } else if (state === 'speaking') {
      playSafe(talkingRef.current);
      pauseSafe(idleRef.current);
      pauseSafe(thinkingRef.current);
    }
  }, [state]);

  const handleVideoLoaded = () => {
    setVideoLoaded(true);
    setHasVideoError(false);
  };

  const handleVideoError = () => {
    // If videos are absent, gracefully show the cybernetic avatar preview
    setHasVideoError(true);
  };

  // State metadata
  const stateColor = state === 'speaking' ? 'var(--green)' 
    : state === 'thinking' ? '#c084fc' 
    : state === 'listening' ? 'var(--cyan)' 
    : 'rgba(0, 212, 255, 0.6)';

  const stateLabel = state === 'speaking' ? '▶ ACTIVE SYNTHESIS'
    : state === 'thinking' ? '⟳ NEURAL PROCESSING'
    : state === 'listening' ? '◉ SENSORY INPUT'
    : '◈ STANDBY COGNITION';

  return (
    <div style={{
      position: 'relative',
      width: '100%',
      height: 220,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(circle at center, rgba(0, 212, 255, 0.05) 0%, rgba(5, 8, 16, 0.9) 80%)',
      borderRadius: 'var(--radius-sm)',
      overflow: 'hidden',
      border: '1px solid rgba(0, 212, 255, 0.15)',
    }}>
      {/* Real Character Videos (when available) */}
      {!hasVideoError && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {/* Idle Video */}
          <video
            ref={idleRef}
            src="/assets/idle.mp4"
            loop
            muted
            playsInline
            autoPlay
            onLoadedData={handleVideoLoaded}
            onError={handleVideoError}
            style={{
              position: 'absolute',
              height: '100%',
              width: '100%',
              objectFit: 'contain',
              opacity: (state === 'idle' || state === 'listening') ? 1 : 0,
              transition: 'opacity 0.25s ease',
            }}
          />

          {/* Thinking Video */}
          <video
            ref={thinkingRef}
            src="/assets/thinking.mp4"
            loop
            muted
            playsInline
            onLoadedData={handleVideoLoaded}
            onError={handleVideoError}
            style={{
              position: 'absolute',
              height: '100%',
              width: '100%',
              objectFit: 'contain',
              opacity: state === 'thinking' ? 1 : 0,
              transition: 'opacity 0.25s ease',
            }}
          />

          {/* Talking / Speaking Video */}
          <video
            ref={talkingRef}
            src="/assets/talking.mp4"
            loop
            muted
            playsInline
            onLoadedData={handleVideoLoaded}
            onError={handleVideoError}
            style={{
              position: 'absolute',
              height: '100%',
              width: '100%',
              objectFit: 'contain',
              opacity: state === 'speaking' ? 1 : 0,
              transition: 'opacity 0.25s ease',
            }}
          />
        </div>
      )}

      {/* Fallback & Cybernetic Avatar Frame (when video assets not yet loaded) */}
      {(!videoLoaded || hasVideoError) && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 10,
          zIndex: 2,
          padding: 16,
          textAlign: 'center',
        }}>
          {/* Holographic Avatar Silhouette */}
          <div style={{
            position: 'relative',
            width: 72,
            height: 72,
            borderRadius: '50%',
            background: 'rgba(0, 20, 40, 0.6)',
            border: `2px solid ${stateColor}`,
            boxShadow: `0 0 24px ${stateColor}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            animation: state === 'speaking' ? 'arc-active-pulse 0.6s infinite' : 'none',
          }}>
            <User size={36} color={stateColor} />
            <div style={{
              position: 'absolute',
              inset: -6,
              borderRadius: '50%',
              border: `1px dashed ${stateColor}`,
              animation: 'arc-spin 10s linear infinite',
            }} />
          </div>

          {/* Persona Status Badge */}
          <div style={{
            fontFamily: 'var(--font-hud)',
            fontSize: 10,
            letterSpacing: 2,
            color: stateColor,
            textShadow: `0 0 10px ${stateColor}`,
          }}>
            {stateLabel}
          </div>

          {/* Asset instructions prompt */}
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 9,
            color: 'var(--text-muted)',
            lineHeight: 1.4,
            maxWidth: 240,
          }}>
            Drop custom video animations into:
            <br />
            <code style={{ color: 'var(--cyan)' }}>frontend/public/assets/</code>
            <br />
            (<code>idle.mp4</code>, <code>thinking.mp4</code>, <code>talking.mp4</code>)
          </div>

          {/* Revert Button */}
          {onSwitchToReactor && (
            <button
              onClick={onSwitchToReactor}
              className="hud-btn"
              style={{
                fontSize: 8,
                padding: '4px 10px',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                marginTop: 2,
              }}
            >
              <RefreshCw size={10} /> REVERT TO ARC REACTOR
            </button>
          )}
        </div>
      )}

      {/* Cybernetic Grid Backdrop */}
      <div style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: 'linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px)',
        backgroundSize: '16px 16px',
        pointerEvents: 'none',
      }} />
    </div>
  );
}
