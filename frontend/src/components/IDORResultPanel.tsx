import type { IDORScanResponse } from '../types';

interface Props {
  result: IDORScanResponse;
  onClose: () => void;
}

const verdictColors: Record<string, string> = {
  vulnerable: '#ef4444',
  blocked: '#10b981',
  inconclusive: '#f59e0b',
};

export default function IDORResultPanel({ result, onClose }: Props) {
  if (!result) return null;
  const vulnerable = result.vulnerable ?? [];
  const blocked = result.blocked ?? [];
  const inconclusive = result.inconclusive ?? [];
  const allItems = [...vulnerable, ...blocked, ...inconclusive];
  const vulnerableCount = vulnerable.length;

  return (
    <div style={{
      background: '#1a1d29', borderRadius: 10,
      border: `1px solid ${vulnerableCount > 0 ? '#ef4444' : '#10b981'}40`,
      overflow: 'hidden', marginTop: 16,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 20px', borderBottom: '1px solid #2a2e3d',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            background: vulnerableCount > 0 ? '#ef4444' : '#10b981', flexShrink: 0,
            boxShadow: `0 0 6px ${vulnerableCount > 0 ? '#ef4444' : '#10b981'}80`,
          }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>
            IDOR Scan
          </span>
          <span style={{ fontSize: 12, color: '#7c8299' }}>
            {result.total_tests} tests · {result.elapsed_ms}ms
          </span>
        </div>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: '#7c8299', cursor: 'pointer',
          fontSize: 16, padding: '2px 8px', borderRadius: 4,
        }} onMouseEnter={e => e.currentTarget.style.background = '#2a2e3d'}
           onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
          ✕
        </button>
      </div>

      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <p style={{ margin: 0, fontSize: 13, color: '#c4c7d0' }}>{result.summary}</p>

        <div style={{ display: 'flex', gap: 16 }}>
          <div>
            <span style={{ display: 'block', fontSize: 10, color: '#7c8299', textTransform: 'uppercase' }}>Vulnerable</span>
            <span style={{ fontSize: 20, fontWeight: 700, color: vulnerableCount > 0 ? '#ef4444' : '#10b981' }}>{vulnerableCount}</span>
          </div>
          <div>
            <span style={{ display: 'block', fontSize: 10, color: '#7c8299', textTransform: 'uppercase' }}>Blocked</span>
            <span style={{ fontSize: 20, fontWeight: 700, color: '#10b981' }}>{result.blocked.length}</span>
          </div>
          <div>
            <span style={{ display: 'block', fontSize: 10, color: '#7c8299', textTransform: 'uppercase' }}>Inconclusive</span>
            <span style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b' }}>{result.inconclusive.length}</span>
          </div>
        </div>

        {allItems.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {allItems.map((item, i) => {
              const color = verdictColors[item.verdict] || '#7c8299';
              return (
                <div key={i} style={{
                  display: 'flex', flexDirection: 'column', gap: 4,
                  background: '#12141f', borderRadius: 6, padding: '10px 12px',
                  borderLeft: `3px solid ${color}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
                      color, background: `${color}20`, padding: '2px 6px',
                      borderRadius: 4,
                    }}>{item.verdict}</span>
                    <span style={{ fontSize: 12, color: '#e2e4e9', fontWeight: 500 }}>
                      {item.parameter}={item.probe_value}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: '#7c8299' }}>
                    {item.reason}
                  </div>
                  <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#7c8299' }}>
                    <span>Baseline: {item.baseline_status}</span>
                    <span>Probe: {item.probe_status}</span>
                    <span>Body diff: {(item.body_diff_ratio * 100).toFixed(1)}%</span>
                  </div>
                  {item.sensitive_fields_leaked.length > 0 && (
                    <div style={{ fontSize: 11, color: '#ef4444' }}>
                      Sensitive data leaked: {item.sensitive_fields_leaked.join(', ')}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
