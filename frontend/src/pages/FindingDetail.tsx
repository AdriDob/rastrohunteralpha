import { useParams, useNavigate } from 'react-router-dom';
import { useFindings } from '../lib/query';

const backBtnStyle: React.CSSProperties = {
  background: 'none', border: 'none', color: '#7c3aed', cursor: 'pointer',
  fontSize: 13, padding: 0, marginBottom: 16, display: 'inline-block',
};

export default function FindingDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const fid = id ? parseInt(id) : null;
  const { data: findings } = useFindings();

  const finding = findings?.items?.find((f) => f.id === fid);

  if (!finding) return <p style={{ color: '#7c8299' }}>Loading…</p>;

  return (
    <div>
      <button onClick={() => navigate('/pipeline')} style={backBtnStyle}>← Back to Pipeline</button>

      <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: 24, marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, color: '#fff' }}>{finding.title}</h2>
        <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
          <div>
            <span style={labelStyle}>Severity</span>
            <span style={{
              ...valStyle,
              color: ({ critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#6b7280' } as Record<string, string>)[finding.severity] ?? '#6b7280',
            }}>
              {finding.severity.toUpperCase()}
            </span>
          </div>
          <div><span style={labelStyle}>Target</span><span style={valStyle}>{finding.target_name}</span></div>
          <div><span style={labelStyle}>Est. Payout</span><span style={valStyle}>${finding.payout.toLocaleString()}</span></div>
          {finding.endpoint_path && (
            <div><span style={labelStyle}>Endpoint</span><span style={valStyle}>{finding.endpoint_path}</span></div>
          )}
        </div>
        {finding.description && (
          <div style={{ marginTop: 16 }}>
            <span style={labelStyle}>Description</span>
            <p style={{ margin: '4px 0 0', fontSize: 13, color: '#c4c7d0', lineHeight: 1.5 }}>{finding.description}</p>
          </div>
        )}
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2,
};
const valStyle: React.CSSProperties = {
  fontSize: 14, color: '#e2e4e9', fontWeight: 500,
};
