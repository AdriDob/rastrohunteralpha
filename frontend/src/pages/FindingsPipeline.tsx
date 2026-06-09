import { useState } from 'react';
import { usePipeline } from '../lib/query';
import { useStore } from '../lib/store';
import { useNavigate } from 'react-router-dom';
import DataTable from '../components/tables/DataTable';
import KPICard from '../components/layout/KPICard';
import { createColumnHelper } from '@tanstack/react-table';
import type { Finding } from '../types';

const helper = createColumnHelper<Finding>();
const columns = [
  helper.accessor('title', { header: 'Title' }),
  helper.accessor('severity', { header: 'Severity', cell: (c) => (
    <span style={{ color: { critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#6b7280' }[c.getValue()] ?? '#6b7280' }}>
      {c.getValue().toUpperCase()}
    </span>
  )}),
  helper.accessor('target_name', { header: 'Target' }),
  helper.accessor('payout', { header: 'Payout', cell: (c) => `$${c.getValue().toLocaleString()}` }),
];

const stages = ['detected', 'validated', 'confirmed', 'reported'] as const;

const selectStyle: React.CSSProperties = {
  background: '#161a26', border: '1px solid #2a2e3d', borderRadius: 6,
  padding: '10px 14px', color: '#e2e4e9', fontSize: 13, width: 240,
  outline: 'none', marginBottom: 16,
};

export default function FindingsPipeline() {
  const { data: pipeline } = usePipeline();
  const setSelectedFinding = useStore((s) => s.setSelectedFinding);
  const navigate = useNavigate();
  const [stage, setStage] = useState<string>('detected');

  const counts = pipeline
    ? { detected: pipeline.detected.length, validated: pipeline.validated.length, confirmed: pipeline.confirmed.length, reported: pipeline.reported.length }
    : { detected: 0, validated: 0, confirmed: 0, reported: 0 };

  const currentFindings = pipeline?.[stage as keyof typeof pipeline] ?? [];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Findings Pipeline</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>Track findings from detection through reporting</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {stages.map((s) => (
          <KPICard key={s} label={s.charAt(0).toUpperCase() + s.slice(1)} value={counts[s]} />
        ))}
      </div>

      <select value={stage} onChange={(e) => setStage(e.target.value)} style={selectStyle}>
        {stages.map((s) => (
          <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
        ))}
      </select>

      <DataTable
        data={currentFindings as any}
        columns={columns as any}
        pageSize={20}
        onRowClick={(row) => {
          setSelectedFinding((row as any).id);
          navigate(`/finding/${(row as any).id}`);
        }}
      />
    </div>
  );
}
