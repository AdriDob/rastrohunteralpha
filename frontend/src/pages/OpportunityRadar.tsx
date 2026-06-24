import { useState, useCallback } from 'react';
import { useOpportunities } from '../lib/query';
import { useUI } from '../lib/store';
import { useNavigate } from 'react-router-dom';
import DataTable from '../components/tables/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import type { Opportunity, PaginationState, SortingState } from '../types';
import { useTechnologyDistribution } from '../lib/query';

const helper = createColumnHelper<Opportunity>();
const columns = [
  helper.accessor('name', { header: 'Target' }),
  helper.accessor('domain', { header: 'Domain' }),
  helper.accessor('roi', { header: 'ROI', cell: (c) => c.getValue()?.toFixed(1) ?? '—' }),
  helper.accessor('max_risk', { header: 'Risk', cell: (c) => c.getValue() != null ? Math.round(c.getValue()) : '—' }),
  helper.accessor('endpoint_count', { header: 'Endpoints' }),
  helper.accessor('finding_count', { header: 'Findings' }),
  helper.accessor('estimated_payout', { header: 'Est. Payout', cell: (c) => c.getValue() != null ? `$${Number(c.getValue()).toLocaleString()}` : '—' }),
  helper.accessor('surfaces', { header: 'Surfaces', cell: (c) => (c.getValue() || []).join(', ') }),
  helper.accessor('opportunity_score', { header: 'Opportunity', cell: (c) => c.getValue()?.toFixed(1) ?? '—' }),
  helper.accessor('competition_score', { header: 'Competition' }),
  helper.accessor('freshness_score', { header: 'Freshness' }),
];

export default function OpportunityRadar() {
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 25 });
  const [sorting, setSorting] = useState<SortingState[]>([{ id: 'roi', desc: true }]);
  const { setSelectedTarget } = useUI();
  const navigate = useNavigate();
  const { data: techDist } = useTechnologyDistribution();

  const handleRowClick = useCallback((row: Opportunity) => {
    setSelectedTarget(row.target_id);
    navigate(`/target/${row.target_id}`);
  }, [setSelectedTarget, navigate]);

  const filters = {
    skip: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
    sort_by: sorting[0]?.id ?? 'roi',
    sort_order: (sorting[0]?.desc ? 'desc' : 'asc') as 'asc' | 'desc',
  };
  const { data } = useOpportunities(filters);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Opportunity Radar</h1>
            <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>All targets ranked by ROI — click any row to drill down</p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {techDist && techDist.length > 0 && (
              <span style={{ fontSize: 11, color: '#7c8299' }}>{techDist.length} tech stacks</span>
            )}
            <div
              onClick={() => navigate('/programs')}
              style={{
                padding: '6px 12px', borderRadius: 6, cursor: 'pointer',
                background: '#1e2230', border: '1px solid #2a2e3d',
                fontSize: 12, color: '#c4c7d0', fontWeight: 600,
              }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#7c3aed'; e.currentTarget.style.color = '#fff'; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2a2e3d'; e.currentTarget.style.color = '#c4c7d0'; }}
            >
              Program Catalog →
            </div>
          </div>
        </div>
      </div>
      <DataTable
        data={items as any}
        columns={columns as any}
        pageSize={25}
        manual
        pageCount={Math.ceil(total / pagination.pageSize)}
        total={total}
        pagination={pagination as any}
        sorting={sorting as any}
        onPaginationChange={setPagination as any}
        onSortingChange={setSorting as any}
        onRowClick={handleRowClick as any}
      />
    </div>
  );
}
