import type { ValidationResult } from '../types';

interface Props {
  result: ValidationResult;
  onClose: () => void;
}

const statusColors: Record<string, string> = {
  confirmed: '#10b981',
  rejected: '#ef4444',
  inconclusive: '#f59e0b',
};

export default function ValidationResultPanel({ result, onClose }: Props) {
  if (!result) return null;
  const { verdict, evidence } = result;
  if (!verdict) return null;
  const color = statusColors[verdict.status] || '#7c8299';

  return (
    <div style={{
      background: '#1a1d29', borderRadius: 10, border: `1px solid ${color}40`,
      overflow: 'hidden', marginTop: 16,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 20px', borderBottom: '1px solid #2a2e3d',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 10, height: 10, borderRadius: '50%', background: color, flexShrink: 0,
            boxShadow: `0 0 6px ${color}80`,
          }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>
            Verdict: {verdict.status.toUpperCase()}
          </span>
          <span style={{ fontSize: 12, color: '#7c8299' }}>
            {(verdict.confidence * 100).toFixed(0)}% confidence
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
        {verdict.summary && (
          <p style={{ margin: 0, fontSize: 13, color: '#c4c7d0', lineHeight: 1.5 }}>
            {verdict.summary}
          </p>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8 }}>
          <div>
            <span style={{ display: 'block', fontSize: 10, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5 }}>Risk Score</span>
            <span style={{ fontSize: 14, color: '#e2e4e9', fontWeight: 500 }}>{verdict.risk_score.toFixed(1)}</span>
          </div>
          <div>
            <span style={{ display: 'block', fontSize: 10, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5 }}>Label</span>
            <span style={{ fontSize: 14, color: '#e2e4e9', fontWeight: 500 }}>{verdict.label}</span>
          </div>
          {verdict.detection_engine && (
            <div>
              <span style={{ display: 'block', fontSize: 10, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5 }}>Engine</span>
              <span style={{ fontSize: 14, color: '#e2e4e9', fontWeight: 500 }}>{verdict.detection_engine}</span>
            </div>
          )}
        </div>

        {verdict.curl_command && (
          <div>
            <span style={{ display: 'block', fontSize: 10, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>PoC cURL</span>
            <pre style={{
              background: '#12141f', borderRadius: 6, padding: 12, margin: 0,
              fontSize: 12, color: '#c4c7d0', overflowX: 'auto', whiteSpace: 'pre-wrap',
              wordBreak: 'break-all', fontFamily: 'monospace',
            }}>{verdict.curl_command}</pre>
          </div>
        )}

        {evidence.length > 0 && (
          <div>
            <span style={{ display: 'block', fontSize: 10, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 }}>
              Evidence ({evidence.length})
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {evidence.slice(0, 5).map((ev: any) => (
                <div key={ev.id} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  background: '#12141f', borderRadius: 6, padding: '8px 12px',
                }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: ev.consistent ? '#10b981' : '#ef4444', flexShrink: 0,
                  }} />
                  <span style={{ fontSize: 12, color: '#c4c7d0', flex: 1 }}>
                    {ev.request_method} {ev.request_url}
                  </span>
                  {ev.response_status !== null && (
                    <span style={{
                      fontSize: 11, fontWeight: 600,
                      color: ev.response_status < 400 ? '#10b981' : '#ef4444',
                    }}>
                      {ev.response_status}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {result.report && (
          <div style={{
            background: '#7c3aed20', borderRadius: 6, padding: '8px 12px',
            border: '1px solid #7c3aed40', fontSize: 12, color: '#c4c7d0',
          }}>
            Report generated successfully
          </div>
        )}
      </div>
    </div>
  );
}
