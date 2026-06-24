import { useState, useCallback } from 'react';
import { usePipeline, useCreateReport } from '../lib/query';
import { useUI } from '../lib/store';
import { useNavigate, useSearchParams } from 'react-router-dom';
import DataTable from '../components/tables/DataTable';
import KPICard from '../components/layout/KPICard';
import { createColumnHelper } from '@tanstack/react-table';
import type { Finding } from '../types';
import { useIsMobile } from '../lib/useIsMobile';

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
  helper.display({
    id: 'actions',
    header: '',
    cell: ({ row }) => <PromoteButton finding={row.original} />,
    enableSorting: false,
  }),
];

const stages = ['detected', 'validated', 'confirmed', 'reported'] as const;

const selectStyle: React.CSSProperties = {
  background: '#161a26', border: '1px solid #2a2e3d', borderRadius: 6,
  padding: '10px 14px', color: '#e2e4e9', fontSize: 13, width: 240,
  outline: 'none', marginBottom: 16,
};

const btnStyle: React.CSSProperties = {
  padding: '4px 10px', borderRadius: 4, border: '1px solid #7c3aed',
  background: '#12141f', color: '#a78bfa', fontSize: 10, fontWeight: 600,
  cursor: 'pointer', whiteSpace: 'nowrap',
};

function PromoteButton({ finding }: { finding: Finding }) {
  const createReport = useCreateReport();
  const navigate = useNavigate();

  const handlePromote = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    createReport.mutate(
      { finding_ids: [finding.id], target: finding.target_name },
      {
        onSuccess: (result) => {
          navigate(`/reports/${result.id}`);
        },
        onError: () => {
          // report promotion failed silently
        },
      },
    );
  }, [finding.id, finding.target_name, createReport, navigate]);

  return (
    <button
      onClick={handlePromote}
      disabled={createReport.isPending}
      style={{
        ...btnStyle,
        opacity: createReport.isPending ? 0.5 : 1,
      }}
    >
      {createReport.isPending ? '...' : 'Promote'}
    </button>
  );
}

export default function FindingsPipeline() {
  const [searchParams] = useSearchParams();
  const investigationId = searchParams.get('investigationId');
  const { data: pipeline } = usePipeline();
  const isMobile = useIsMobile();
  const { setSelectedFinding } = useUI();
  const navigate = useNavigate();
  const [stage, setStage] = useState<string>('detected');

  const counts = pipeline
    ? { detected: pipeline.detected.length, validated: pipeline.validated.length, confirmed: pipeline.confirmed.length, reported: pipeline.reported.length }
    : { detected: 0, validated: 0, confirmed: 0, reported: 0 };

  const currentFindings = pipeline?.[stage as keyof typeof pipeline] ?? [];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Findings Pipeline</h1>
          {investigationId && (
            <span style={{
              fontSize: 10, background: '#7c3aed20', color: '#a78bfa',
              padding: '3px 10px', borderRadius: 10, fontWeight: 600,
            }}>
              Investigation #{investigationId}
            </span>
          )}
        </div>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>
          {investigationId
            ? 'Pipeline findings scoped to the current investigation'
            : 'Track findings from detection through reporting'}
        </p>
      </div>

      {investigationId && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button
            onClick={() => navigate(`/investigation/${investigationId}`)}
            style={{
              padding: '6px 12px', borderRadius: 6, border: '1px solid #7c3aed',
              background: '#12141f', color: '#a78bfa', fontSize: 11, fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            ← Back to Investigation
          </button>
        </div>
      )}

      {currentFindings.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#7c8299', background: '#1a1d29', borderRadius: 8, border: '1px solid #2a2e3d' }}>
          <p style={{ fontSize: 14, margin: 0 }}>No findings in "{stage}" stage.</p>
          <p style={{ fontSize: 12, margin: '8px 0 0', color: '#4a4f63' }}>Findings appear here as they move through the pipeline.</p>
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
            {stages.map((s) => (
              <KPICard key={s} label={s.charAt(0).toUpperCase() + s.slice(1)} value={counts[s]} />
            ))}
          </div>

          <select value={stage} onChange={(e) => setStage(e.target.value)} style={{ ...selectStyle, width: isMobile ? '100%' : 240 }}>
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
        </>
      )}
    </div>
  );
}
