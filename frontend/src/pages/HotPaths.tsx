import { useEndpoints } from '../lib/query';
import { useStore } from '../lib/store';
import { useNavigate } from 'react-router-dom';
import DataTable from '../components/tables/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import type { Endpoint } from '../types';

const helper = createColumnHelper<Endpoint>();
const columns = [
  helper.accessor('target_id', { header: 'Target ID' }),
  helper.accessor('path', { header: 'Path' }),
  helper.accessor('method', { header: 'Method' }),
  helper.accessor('risk_score', { header: 'Risk', cell: (c) => Math.round(c.getValue()) }),
  helper.accessor('confidence', { header: 'Confidence', cell: (c) => (c.getValue() * 100).toFixed(0) + '%' }),
  helper.accessor('vector', { header: 'Vector' }),
  helper.accessor('actionable', { header: 'Actionable', cell: (c) => (c.getValue() ? 'Yes' : 'No') }),
];

export default function HotPaths() {
  const { data: res } = useEndpoints(null, { limit: 500, sort_by: 'risk_score', sort_order: 'desc' });
  const setSelectedEndpoint = useStore((s) => s.setSelectedEndpoint);
  const navigate = useNavigate();

  const all = res?.items ?? [];
  const hot = all.filter((e) => e.risk_score >= 25);

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Hot Paths</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>High-risk endpoints ranked by score — click to investigate</p>
      </div>
      <DataTable
        data={hot as any}
        columns={columns as any}
        pageSize={25}
        onRowClick={(row) => {
          setSelectedEndpoint((row as any).id);
          navigate(`/endpoint/${(row as any).id}`);
        }}
      />
    </div>
  );
}
