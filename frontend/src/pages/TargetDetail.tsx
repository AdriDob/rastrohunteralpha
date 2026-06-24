import { useParams, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useTarget, useEndpoints } from '../lib/query';
import { useUI, useAuth } from '../lib/store';
import { updateSession } from '../lib/api';
import FavoriteButton from '../components/FavoriteButton';
import DataTable from '../components/tables/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import type { Endpoint, PaginationState } from '../types';

const helper = createColumnHelper<Endpoint>();
const columns = [
  helper.accessor('method', { header: 'Method' }),
  helper.accessor('path', { header: 'Path' }),
  helper.accessor('risk_score', { header: 'Risk', cell: (c) => Math.round(c.getValue()) }),
  helper.accessor('vector', { header: 'Vector' }),
  helper.accessor('actionable', { header: 'Actionable', cell: (c) => (c.getValue() ? 'Yes' : 'No') }),
];

const backBtnStyle: React.CSSProperties = {
  background: 'none', border: 'none', color: '#7c3aed', cursor: 'pointer',
  fontSize: 13, padding: 0, marginBottom: 16, display: 'inline-block',
};

export default function TargetDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const tid = id ? parseInt(id) : null;
  const { data: target } = useTarget(tid);
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 15 });
  const { data: endpointsRes } = useEndpoints(tid, {
    skip: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
  });
  const { setSelectedEndpoint } = useUI();
  const { setSession } = useAuth();
  useEffect(() => {
    if (target) {
      updateSession({ current_target_id: target.id }).then(r => {
        setSession({ id: r.id, name: '', current_target_id: target.id, current_investigation: null, open_evidence_ids: [], current_replay_id: null, current_report_draft: null, updated_at: '' });
      }).catch(() => {});
    }
  }, [target, setSession]);

  if (!target) return <p style={{ color: '#7c8299' }}>Loading…</p>;

  const items = endpointsRes?.items ?? [];
  const total = endpointsRes?.total ?? 0;

  return (
    <div>
      <button onClick={() => navigate('/radar')} style={backBtnStyle}>← Back to Radar</button>

      <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: 20, marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <h2 style={{ margin: 0, fontSize: 18, color: '#fff' }}>{target.name}</h2>
          <FavoriteButton itemType="target" itemId={target.id} label={target.name} />
          <button
            onClick={() => navigate(`/hypothesis?targetId=${target.id}`)}
            style={{
              marginLeft: 'auto', background: '#7c3aed', border: 'none',
              borderRadius: 6, padding: '6px 14px', color: '#fff',
              fontSize: 11, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Generate Hypotheses
          </button>
        </div>
        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 8 }}>
          <div><span style={labelStyle}>Domain</span><span style={valStyle}>{target.domain ?? '—'}</span></div>
          <div><span style={labelStyle}>Risk</span><span style={valStyle}>{Math.round(target.max_risk)}</span></div>
          <div><span style={labelStyle}>ROI</span><span style={valStyle}>{target.roi.toFixed(1)}</span></div>
          <div><span style={labelStyle}>Endpoints</span><span style={valStyle}>{target.endpoint_count}</span></div>
          <div><span style={labelStyle}>Findings</span><span style={valStyle}>{target.finding_count}</span></div>
          <div><span style={labelStyle}>Confirmed</span><span style={valStyle}>{target.confirmed_count}</span></div>
          <div><span style={labelStyle}>Est. Payout</span><span style={valStyle}>${target.estimated_payout.toLocaleString()}</span></div>
          <div><span style={labelStyle}>Surfaces</span><span style={valStyle}>{target.surfaces.join(', ') || '—'}</span></div>
        </div>
      </div>

      <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 12px', color: '#fff' }}>Endpoints</h3>
      <DataTable
        data={items as any}
        columns={columns as any}
        pageSize={15}
        manual
        pageCount={Math.ceil(total / pagination.pageSize)}
        total={total}
        pagination={pagination as any}
        onPaginationChange={setPagination as any}
        onRowClick={(row) => {
          setSelectedEndpoint((row as any).id);
          navigate(`/endpoint/${(row as any).id}`);
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
