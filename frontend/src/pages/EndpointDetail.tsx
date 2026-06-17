import { useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useEndpoint, useFindings, useValidateEndpoint, useScanIDOR } from '../lib/query';
import { useStore } from '../lib/store';
import FavoriteButton from '../components/FavoriteButton';
import ValidationResultPanel from '../components/ValidationResultPanel';
import IDORResultPanel from '../components/IDORResultPanel';
import DataTable from '../components/tables/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import type { Finding, PaginationState, ValidationResult, IDORScanResponse } from '../types';

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
  const validateMutation = useValidateEndpoint();
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const idorMutation = useScanIDOR();
  const [idorResult, setIdorResult] = useState<IDORScanResponse | null>(null);

  if (!endpoint) return <p style={{ color: '#7c8299' }}>Loading…</p>;

  const items = findingsRes?.items ?? [];
  const total = findingsRes?.total ?? 0;

  const handleValidate = () => {
    const hotPathId = `manual-${endpoint.id}-${Date.now()}`;
    validateMutation.mutate(
      {
        hot_path_id: hotPathId,
        endpoint_id: endpoint.id,
        target_id: endpoint.target_id,
        url: endpoint.path,
        method: endpoint.method,
        min_attempts: 3,
      },
      {
        onSuccess: (res) => setValidationResult(res),
      },
    );
  };

  const handleIDOR = () => {
    idorMutation.mutate(
      {
        target_id: endpoint.target_id,
        endpoint_id: endpoint.id,
        url: `https://${endpoint.path}`,
        method: endpoint.method,
        identity_baseline_id: 0,
      },
      {
        onSuccess: (res) => setIdorResult(res),
      },
    );
  };

  return (
    <div>
      <button onClick={() => navigate('/hot-paths')} style={backBtnStyle}>← Back to Hot Paths</button>

      <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: 20, marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <h2 style={{ margin: 0, fontSize: 18, color: '#fff' }}>{endpoint.method} {endpoint.path}</h2>
          <FavoriteButton itemType="endpoint" itemId={endpoint.id} label={`${endpoint.method} ${endpoint.path}`} />
        </div>
        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 8 }}>
          <div><span style={labelStyle}>Risk Score</span><span style={valStyle}>{Math.round(endpoint.risk_score)}</span></div>
          <div><span style={labelStyle}>Confidence</span><span style={valStyle}>{(endpoint.confidence * 100).toFixed(0)}%</span></div>
          <div><span style={labelStyle}>Vector</span><span style={valStyle}>{endpoint.vector}</span></div>
          <div><span style={labelStyle}>Labels</span><span style={valStyle}>{endpoint.labels.join(', ') || '—'}</span></div>
        </div>
        <div style={{ marginTop: 16, display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={handleValidate} disabled={validateMutation.isPending} style={{
            background: validateMutation.isPending ? '#4a1d96' : '#7c3aed',
            border: 'none', color: '#fff', padding: '8px 20px', borderRadius: 6,
            cursor: validateMutation.isPending ? 'not-allowed' : 'pointer',
            fontSize: 13, fontWeight: 500,
          }}>
            {validateMutation.isPending ? 'Validating…' : 'Validate'}
          </button>
          <button onClick={handleIDOR} disabled={idorMutation.isPending} style={{
            background: idorMutation.isPending ? '#4a1d96' : '#7c3aed',
            border: 'none', color: '#fff', padding: '8px 20px', borderRadius: 6,
            cursor: idorMutation.isPending ? 'not-allowed' : 'pointer',
            fontSize: 13, fontWeight: 500,
          }}>
            {idorMutation.isPending ? 'Scanning…' : 'IDOR Scan'}
          </button>
          {validateMutation.isError && (
            <span style={{ fontSize: 12, color: '#ef4444' }}>
              Validation failed: {(validateMutation.error as any)?.message || 'Unknown error'}
            </span>
          )}
          {idorMutation.isError && (
            <span style={{ fontSize: 12, color: '#ef4444' }}>
              IDOR scan failed: {(idorMutation.error as any)?.message || 'Unknown error'}
            </span>
          )}
        </div>
      </div>

      {validationResult && (
        <ValidationResultPanel
          result={validationResult}
          onClose={() => setValidationResult(null)}
        />
      )}

      {idorResult && (
        <IDORResultPanel
          result={idorResult}
          onClose={() => setIdorResult(null)}
        />
      )}

      <h3 style={{ fontSize: 16, fontWeight: 600, margin: '16px 0 12px', color: '#fff' }}>Findings on this Endpoint</h3>
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
