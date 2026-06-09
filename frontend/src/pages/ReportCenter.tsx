import { useReport, useFindings } from '../lib/query';
import KPICard from '../components/layout/KPICard';
import { useState } from 'react';

const btnStyle: React.CSSProperties = {
  background: '#7c3aed', border: 'none', borderRadius: 6,
  color: '#fff', padding: '10px 20px', cursor: 'pointer', fontSize: 13,
  fontWeight: 600, transition: 'background 0.15s',
};

const btnStyle2: React.CSSProperties = {
  ...btnStyle, background: '#1e2230', border: '1px solid #2a2e3d',
};

export default function ReportCenter() {
  const { data: findingsRes } = useFindings(undefined, undefined, { limit: 500 });
  const { refetch, isFetching } = useReport();
  const [showPreview, setShowPreview] = useState(false);
  const [preview, setPreview] = useState('');

  const findings = findingsRes?.items ?? [];
  const totalFindings = findings.length;
  const confirmed = findings.filter((f) => f.severity === 'critical' || f.severity === 'high').length;
  const totalValue = findings.reduce((s, f) => s + f.payout, 0);

  const handleGenerate = async () => {
    const res = await refetch();
    if (res.data) {
      setPreview(res.data.markdown);
      setShowPreview(true);
    }
  };

  const handleExport = () => {
    if (!preview) return;
    const blob = new Blob([preview], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'rastro_report.md';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Report Center</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>Generate and export bug bounty reports</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
        <KPICard label="Total Findings" value={totalFindings} />
        <KPICard label="High+Critical" value={confirmed} />
        <KPICard label="Est. Total Value" value={`$${totalValue.toLocaleString()}`} />
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button onClick={handleGenerate} disabled={isFetching} style={btnStyle}>
          {isFetching ? 'Generating…' : 'Generate Markdown Report'}
        </button>
        <button onClick={handleExport} disabled={!preview} style={btnStyle2}>Export Report</button>
      </div>

      {showPreview && preview && (
        <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, margin: '0 0 12px', color: '#fff' }}>Report Preview</h3>
          <pre style={{
            background: '#0d0f14', padding: 16, borderRadius: 6, border: '1px solid #1e2230',
            fontSize: 12, color: '#e2e4e9', maxHeight: 500, overflow: 'auto',
            whiteSpace: 'pre-wrap', margin: 0,
          }}>{preview}</pre>
        </div>
      )}
    </div>
  );
}
