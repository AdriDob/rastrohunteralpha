import { useEffect, useState } from 'react';

interface BootScreenProps {
  onComplete: () => void;
}

const BOOT_PHASES = [
  { label: 'Authenticating session', duration: 400 },
  { label: 'Resolving identity', duration: 300 },
  { label: 'Hydrating memory', duration: 400 },
  { label: 'Loading intelligence', duration: 400 },
  { label: 'Generating briefing', duration: 300 },
  { label: 'Initializing assistant', duration: 300 },
];

export default function BootScreen({ onComplete }: BootScreenProps) {
  const [phase, setPhase] = useState(0);
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    if (phase >= BOOT_PHASES.length) {
      setFadeOut(true);
      const t = setTimeout(() => onComplete(), 400);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setPhase((p) => p + 1), BOOT_PHASES[phase].duration);
    return () => clearTimeout(t);
  }, [phase, onComplete]);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: '#13151d',
      opacity: fadeOut ? 0 : 1,
      transition: 'opacity 0.4s ease-out',
    }}>
      <div style={{
        fontSize: 36, fontWeight: 800, letterSpacing: '-0.03em',
        color: '#fff', marginBottom: 48,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <span style={{ color: '#7c3aed' }}>R</span>astro
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, width: 280 }}>
        {BOOT_PHASES.map((p, i) => {
          const status = i < phase ? 'done' : i === phase ? 'active' : 'pending';
          return (
            <div key={p.label} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              opacity: status === 'pending' ? 0.3 : 1,
              transition: 'all 0.3s ease',
            }}>
              <div style={{
                width: 20, height: 20, borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10, fontWeight: 700,
                background: status === 'done' ? '#22c55e'
                  : status === 'active' ? '#7c3aed' : '#2a2e3d',
                color: status === 'pending' ? '#4a4f63' : '#fff',
                transition: 'all 0.3s ease',
              }}>
                {status === 'done' ? '✓' : status === 'active' ? '○' : '·'}
              </div>
              <div style={{ fontSize: 13, color: status === 'pending' ? '#4a4f63' : '#e2e4e9' }}>
                {p.label}
              </div>
              {status === 'active' && (
                <div style={{
                  width: 12, height: 12, borderRadius: '50%',
                  border: '2px solid #7c3aed',
                  borderTopColor: 'transparent',
                  animation: 'spin 0.8s linear infinite',
                  marginLeft: 'auto',
                }} />
              )}
            </div>
          );
        })}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
      `}</style>
    </div>
  );
}
