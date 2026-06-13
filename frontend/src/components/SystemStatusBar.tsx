import { useSystemState, formatUptime, stateColor } from '../lib/api/system';

interface SystemStatusBarProps {
  style?: React.CSSProperties;
}

export default function SystemStatusBar({ style }: SystemStatusBarProps) {
  const { data } = useSystemState();
  const status = data?.state;

  if (!status) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 6, background: '#1e2230', border: '1px solid #2a2e3d', fontSize: 11, color: '#7c8299', ...style }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#6b7280', animation: 'pulse 2s infinite' }} />
        Connecting...
      </div>
    );
  }

  const color = stateColor(status.system_state);
  const label = status.system_state === 'READY' ? 'Healthy'
    : status.system_state === 'DEGRADED' ? `Degraded (${status.services_unhealthy} issues)`
    : status.system_state === 'FAILED' ? 'Failed'
    : 'Booting';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '4px 10px', borderRadius: 6,
      background: '#1e2230', border: '1px solid #2a2e3d',
      fontSize: 11, color: '#7c8299', ...style,
    }}>
      <div style={{ width: 6, height: 6, borderRadius: '50%', background: color, boxShadow: `0 0 6px ${color}40` }} />
      <span>{label}</span>
      <span style={{ color: '#4a4f63' }}>·</span>
      <span>Uptime {formatUptime(status.uptime_seconds)}</span>
      {status.services_unhealthy > 0 && (
        <span style={{ color: '#f59e0b' }}>({status.services_healthy}/{status.services_total} ok)</span>
      )}
    </div>
  );
}
