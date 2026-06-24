import { useState, useCallback } from 'react';
import { usePrograms, useTechnologyDistribution, useFetchPublicPrograms } from '../lib/query';
import DataTable from '../components/tables/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import type { ProgramItem, PaginationState, SortingState } from '../types';

const helper = createColumnHelper<ProgramItem>();
const columns = [
  helper.accessor('name', { header: 'Program' }),
  helper.accessor('source', { header: 'Platform' }),
  helper.accessor('cms_detected', { header: 'CMS' }),
  helper.accessor('framework_detected', { header: 'Framework' }),
  helper.accessor('technology_tags', {
    header: 'Technologies',
    cell: (c) => {
      const tags = c.getValue() || [];
      return tags.length ? tags.slice(0, 4).join(', ') + (tags.length > 4 ? '...' : '') : '-';
    },
  }),
  helper.accessor('quality_score', { header: 'Quality', cell: (c) => c.getValue() ?? '-' }),
  helper.accessor('roi_score', { header: 'ROI', cell: (c) => c.getValue() ?? '-' }),
  helper.accessor('opportunity_score', {
    header: 'Opportunity',
    cell: (c) => c.getValue()?.toFixed(1) ?? '-',
  }),
];

export default function ProgramCatalog() {
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 25 });
  const [sorting, setSorting] = useState<SortingState[]>([{ id: 'name', desc: false }]);
  const [techFilter, setTechFilter] = useState('');

  const filters = {
    skip: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
    sort_by: sorting[0]?.id ?? 'name',
    sort_order: (sorting[0]?.desc ? 'desc' : 'asc') as 'asc' | 'desc',
    technology: techFilter,
  };
  const { data } = usePrograms(filters);
  const { data: techDist } = useTechnologyDistribution();
  const fetchMutation = useFetchPublicPrograms();

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const handleRowClick = useCallback((row: ProgramItem) => {
    window.open(`/target/${row.id}`, '_blank');
  }, []);

  const handleFetch = useCallback((platform?: string) => {
    fetchMutation.mutate(platform ? [platform] : undefined);
  }, [fetchMutation]);

  const style: Record<string, React.CSSProperties> = {
    header: { fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' },
    subtitle: { margin: '4px 0 0', fontSize: 13, color: '#7c8299' },
    toolbar: { display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 16 },
    techBadge: {
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 4,
      fontSize: 11,
      fontWeight: 600,
      cursor: 'pointer',
      border: '1px solid #2a2d3a',
      marginRight: 4,
      marginBottom: 4,
    },
    activeBadge: {
      background: '#1a3a5c',
      color: '#60b0ff',
      border: '1px solid #2a6db5',
    },
    fetchBtn: {
      padding: '6px 14px',
      borderRadius: 6,
      border: '1px solid #2a2d3a',
      background: '#1a1d2e',
      color: '#c8cce0',
      fontSize: 12,
      cursor: 'pointer',
    },
    fetchBtnPrimary: {
      background: '#2a6db5',
      color: '#fff',
      border: '1px solid #3a7dc5',
    },
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={style.header}>Program Catalog</h1>
        <p style={style.subtitle}>
          Discovered public bug bounty programs with technology fingerprinting
        </p>
      </div>

      <div style={style.toolbar}>
        <button
          style={{ ...style.fetchBtn, ...style.fetchBtnPrimary }}
          onClick={() => handleFetch()}
          disabled={fetchMutation.isPending}
        >
          {fetchMutation.isPending ? 'Fetching...' : 'Fetch All Platforms'}
        </button>
        {['hackerone', 'bugcrowd', 'intigriti', 'yeswehack'].map((p) => (
          <button
            key={p}
            style={style.fetchBtn}
            onClick={() => handleFetch(p)}
            disabled={fetchMutation.isPending}
          >
            {p}
          </button>
        ))}
      </div>

      {(techDist && techDist.length > 0) && (
        <div style={{ ...style.toolbar, marginBottom: 12 }}>
          <span style={{ fontSize: 12, color: '#7c8299', marginRight: 8 }}>Filter by tech:</span>
          <button
            style={{ ...style.techBadge, ...(techFilter === '' ? style.activeBadge : {}) }}
            onClick={() => setTechFilter('')}
          >
            All
          </button>
          {techDist.slice(0, 20).map((t) => (
            <button
              key={t.technology}
              style={{ ...style.techBadge, ...(techFilter === t.technology ? style.activeBadge : {}) }}
              onClick={() => setTechFilter(techFilter === t.technology ? '' : t.technology)}
            >
              {t.technology} ({t.count})
            </button>
          ))}
        </div>
      )}

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
