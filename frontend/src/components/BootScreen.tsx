import { useEffect, useState, useRef } from 'react';
import { useSystemState } from '../lib/api/system';

interface BootScreenProps {
  onComplete: () => void;
  licenseError?: string | null;
}

const CHECK_INTERVAL = 500;
const MAX_CHECKS = 60;

const STATE_MESSAGES: Record<string, string> = {
  BOOTING: 'Inicializando sistema...',
  READY: 'Sistema listo',
  DEGRADED: 'Sistema degradado',
  FAILED: 'Error del sistema',
};

function useRealBootState() {
  const { data, isLoading } = useSystemState();
  const [checks, setChecks] = useState(0);

  useEffect(() => {
    if (isLoading) return;
    const interval = setInterval(() => {
      setChecks(c => c + 1);
    }, CHECK_INTERVAL);
    return () => clearInterval(interval);
  }, [isLoading]);

  const isReady = data?.state?.system_state === 'READY' || checks >= MAX_CHECKS;

  return {
    systemState: data?.state,
    services: data?.services ?? [],
    isReady,
    timedOut: checks >= MAX_CHECKS && data?.state?.system_state !== 'READY',
  };
}

export default function BootScreen({ onComplete, licenseError }: BootScreenProps) {
  const { systemState, services, isReady, timedOut } = useRealBootState();
  const [fadeOut, setFadeOut] = useState(false);
  const completedRef = useRef(false);

  useEffect(() => {
    if (completedRef.current) return;
    if ((isReady || timedOut) && !licenseError) {
      completedRef.current = true;
      setFadeOut(true);
      const t = setTimeout(onComplete, 400);
      return () => clearTimeout(t);
    }
  }, [isReady, timedOut, licenseError, onComplete]);

  const healthyCount = services.filter(s => s.state === 'healthy').length;

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: '#0A0B0F',
      opacity: fadeOut ? 0 : 1,
      transition: 'opacity 0.4s ease-out',
    }}>
      {/* Logo */}
      <div style={{
        fontSize: 32, fontWeight: 700, letterSpacing: '0.15em',
        color: '#F8FAFC', marginBottom: 6,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span style={{ color: '#D4AF37', fontWeight: 800 }}>O</span>
        RION
      </div>
      <div style={{
        fontSize: 11, color: '#6B7280', letterSpacing: '0.08em',
        marginBottom: 48, fontWeight: 400,
      }}>
        Automated Security Investigation OS
      </div>

      {licenseError ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, width: 320, alignItems: 'center' }}>
          <div style={{
            width: 48, height: 48, borderRadius: '50%',
            background: 'rgba(239,68,68,0.15)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 24,
          }}>⚠</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#EF4444' }}>
            License required
          </div>
          <div style={{ fontSize: 13, color: '#A0A8B3', textAlign: 'center', lineHeight: 1.5 }}>
            {licenseError}
          </div>
          <button
            onClick={() => window.location.href = '/activate'}
            style={{
              padding: '10px 28px', borderRadius: 8, border: 'none',
              background: '#D4AF37', color: '#0A0B0F', fontSize: 14, fontWeight: 600,
              cursor: 'pointer', marginTop: 8,
            }}
          >
            Activate license
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, width: 280 }}>
          {systemState && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'center',
              fontSize: 13, color: '#A0A8B3',
            }}>
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                background: systemState.system_state === 'READY' ? '#22C55E'
                  : systemState.system_state === 'DEGRADED' ? '#F59E0B'
                  : systemState.system_state === 'FAILED' ? '#EF4444'
                  : '#D4AF37',
                animation: systemState.system_state !== 'READY' ? 'pulse-dot 1.5s ease-in-out infinite' : undefined,
              }} />
              {STATE_MESSAGES[systemState.system_state] || 'Inicializando...'}
            </div>
          )}
          {!systemState && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'center',
              fontSize: 13, color: '#A0A8B3',
            }}>
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                background: '#D4AF37',
                animation: 'pulse-dot 1.5s ease-in-out infinite',
              }} />
              Conectando con el backend...
            </div>
          )}
          {services.length > 0 && (
            <div style={{
              display: 'flex', flexDirection: 'column', gap: 6, marginTop: 16,
            }}>
              {services.slice(0, 6).map(s => (
                <div key={s.name} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  fontSize: 11, color: s.state === 'healthy' ? '#A0A8B3' : '#F59E0B',
                }}>
                  <div style={{
                    width: 5, height: 5, borderRadius: '50%',
                    background: s.state === 'healthy' ? '#22C55E' : '#F59E0B',
                    flexShrink: 0,
                  }} />
                  <span style={{ flex: 1 }}>{s.name}</span>
                  <span style={{ fontSize: 10, color: '#6B7280' }}>{s.state}</span>
                </div>
              ))}
            </div>
          )}
          {systemState && (
            <div style={{
              textAlign: 'center', marginTop: 20,
              fontSize: 10, color: '#4A4F63',
            }}>
              {healthyCount}/{systemState.services_total} servicios operativos
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 0.4; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.3); }
        }
      `}</style>
    </div>
  );
}
