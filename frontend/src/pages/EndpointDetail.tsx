import { useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useEndpoint, useFindings } from '../lib/query';
import { useStore } from '../lib/store';
import DataTable from '../components/tables/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import type { Finding, PaginationState } from '../types';

const findingHelper = createColumnHelper<Finding>();
const findingColumns = [
  findingHelper.accessor('title', { header: 'Title' }),
  findingHelper.accessor('severity', { header: 'Severity', cell: (c) => c.getValue().toUpperCase() }),
  findingHelper.accessor('payout', { header: 'Payout', cell: (c) => `$${c.getValue().toLocaleString()}` }),
];

const backBtnStyle: React.CSSProperties = {
  background: 'none', border: 'none', color: '#7c3aed', cursor: 'pointer',
  fontSize: 13, padding: 0, marginBottom: 16, display: 'inline-block',
};

export default function EndpointDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const eid = id ? parseInt(id) : null;
  const { data: endpoint } = useEndpoint(eid);
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 10 });
  const { data: findingsRes } = useFindings(undefined, eid, {
    skip: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
  });
  const setSelectedFinding = useStore((s) => s.setSelectedFinding);

  if (!endpoint) return <p style={{ color: '#7c8299' }}>Loading…</p>;

  const items = findingsRes?.items ?? [];
  const total = findingsRes?.total ?? 0;

  return (
    <div>
      <button onClick={() => navigate('/hot-paths')} style={backBtnStyle}>← Back to Hot Paths</button>

      <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: 20, marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, color: '#fff' }}>{endpoint.method} {endpoint.path}</h2>
        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 8 }}>
          <div><span style={labelStyle}>Risk Score</span><span style={valStyle}>{Math.round(endpoint.risk_score)}</span></div>
          <div><span style={labelStyle}>Confidence</span><span style={valStyle}>{(endpoint.confidence * 100).toFixed(0)}%</span></div>
          <div><span style={labelStyle}>Vector</span><span style={valStyle}>{endpoint.vector}</span></div>
          <div><span style={labelStyle}>Labels</span><span style={valStyle}>{endpoint.labels.join(', ') || '—'}</span></div>
        </div>
      </div>

      <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 12px', color: '#fff' }}>Findings on this Endpoint</h3>
      <DataTable
        data={items as any}
        columns={findingColumns as any}
        pageSize={10}
        manual
        pageCount={Math.ceil(total / pagination.pageSize)}
        total={total}
        pagination={pagination as any}
        onPaginationChange={setPagination as any}
        onRowClick={(row) => {
          setSelectedFinding((row as any).id);
          navigate(`/finding/${(row as any).id}`);
        }}
      />
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2,
};
const valStyle: React.CSSProperties = {
  fontSize: 14, color: '#e2e4e9', fontWeight: 500,
};
