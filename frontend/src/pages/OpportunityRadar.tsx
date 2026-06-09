import { useState, useCallback } from 'react';
import { useOpportunities } from '../lib/query';
import { useStore } from '../lib/store';
import { useNavigate } from 'react-router-dom';
import DataTable from '../components/tables/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import type { Opportunity, PaginationState, SortingState } from '../types';

const helper = createColumnHelper<Opportunity>();
const columns = [
  helper.accessor('name', { header: 'Target' }),
  helper.accessor('domain', { header: 'Domain' }),
  helper.accessor('roi', { header: 'ROI', cell: (c) => c.getValue().toFixed(1) }),
  helper.accessor('max_risk', { header: 'Risk', cell: (c) => Math.round(c.getValue()) }),
  helper.accessor('endpoint_count', { header: 'Endpoints' }),
  helper.accessor('finding_count', { header: 'Findings' }),
  helper.accessor('estimated_payout', { header: 'Est. Payout', cell: (c) => `$${c.getValue().toLocaleString()}` }),
  helper.accessor('surfaces', { header: 'Surfaces', cell: (c) => (c.getValue() || []).join(', ') }),
  helper.accessor('opportunity_score', { header: 'Opportunity', cell: (c) => c.getValue().toFixed(1) }),
  helper.accessor('competition_score', { header: 'Competition' }),
  helper.accessor('freshness_score', { header: 'Freshness' }),
];

export default function OpportunityRadar() {
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 25 });
  const [sorting, setSorting] = useState<SortingState[]>([{ id: 'roi', desc: true }]);
  const setSelectedTarget = useStore((s) => s.setSelectedTarget);
  const navigate = useNavigate();

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
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Opportunity Radar</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>All targets ranked by ROI — click any row to drill down</p>
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
        onRowClick={(row) => {
          setSelectedTarget((row as any).target_id);
          navigate(`/target/${(row as any).target_id}`);
        }}
      />
    </div>
  );
}
