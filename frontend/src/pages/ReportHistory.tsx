import { useMemo, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { createColumnHelper } from '@tanstack/react-table';
import type { SortingState, PaginationState } from '@tanstack/react-table';
import DataTable from '../components/tables/DataTable';
import Badge from '../components/ui/Badge';
import Panel from '../components/ui/Panel';
import { useReportsList, useReportStats } from '../lib/query';
import type { ReportItem } from '../types';
import { REPORT_STATUSES } from '../types';

const helper = createColumnHelper<ReportItem>();

const STATUS_STYLES: Record<string, { color: string; bg: string }> = {
  draft: { color: '#6b7280', bg: '#6b728018' },
  ready: { color: '#3b82f6', bg: '#3b82f618' },
  submitted: { color: '#8b5cf6', bg: '#8b5cf618' },
  need_more_info: { color: '#f97316', bg: '#f9731618' },
  triaged: { color: '#22c55e', bg: '#22c55e18' },
  resolved: { color: '#06b6d4', bg: '#06b6d418' },
  paid: { color: '#10b981', bg: '#10b98118' },
  duplicate: { color: '#ef4444', bg: '#ef444418' },
  informative: { color: '#eab308', bg: '#eab30818' },
  na: { color: '#6b7280', bg: '#6b728018' },
};

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0, high: 1, medium: 2, low: 3, info: 4,
};

function formatCurrency(amount: number, currency: string): string {
  const symbols: Record<string, string> = { USD: '$', EUR: '€', GBP: '£', BTC: '₿', ETH: 'Ξ' };
  const sym = symbols[currency] || currency + ' ';
  if (amount >= 1000) return sym + (amount / 1000).toFixed(1) + 'k';
  return sym + amount.toLocaleString();
}

function elapsedDays(dateStr: string | null): string {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return '0d';
  if (diff === 0) return 'Today';
  if (diff === 1) return '1d';
  return `${diff}d`;
}

export default function ReportHistory() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [sorting, setSorting] = useState<SortingState>([{ id: 'created_at', desc: true }]);
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 20 });

  const params = useMemo(() => {
    const p: Record<string, unknown> = {
      limit: pagination.pageSize,
      offset: pagination.pageIndex * pagination.pageSize,
      sort_by: sorting[0]?.id || 'created_at',
      sort_order: sorting[0]?.desc ? 'desc' : 'asc',
    };
    if (statusFilter !== 'all') p.status = statusFilter;
    if (search.trim()) p.search = search.trim();
    return p as {
      limit: number; offset: number; sort_by: string; sort_order: string;
      status?: string; search?: string;
    };
  }, [statusFilter, search, sorting, pagination]);

  const { data, isLoading } = useReportsList(params);
  const { data: stats } = useReportStats();

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const handleRowClick = useCallback((row: ReportItem) => {
    navigate(`/reports/${row.id}`);
  }, [navigate]);

  const handleGlobalFilterChange = useCallback((value: string) => {
    setSearch(value);
    setPagination(prev => ({ ...prev, pageIndex: 0 }));
  }, []);

  const columns = useMemo(() => [
    helper.accessor('id', {
      header: 'ID',
      cell: (info) => <span style={{ color: '#7c8299' }}>#{info.getValue()}</span>,
      enableSorting: true,
    }),
    helper.accessor('program', {
      header: 'Program',
      cell: (info) => info.getValue() || '-',
      enableSorting: true,
    }),
    helper.accessor('target', {
      header: 'Target',
      cell: (info) => info.getValue() || '-',
      enableSorting: true,
    }),
    helper.accessor('vulnerability', {
      header: 'Vulnerability',
      cell: (info) => info.getValue() || '-',
    }),
    helper.accessor('severity', {
      header: 'Severity',
      cell: (info) => <Badge variant="severity" text={info.getValue() || 'info'} size="sm" />,
      sortingFn: (a, b) => (SEVERITY_ORDER[a.original.severity] ?? 99) - (SEVERITY_ORDER[b.original.severity] ?? 99),
      enableSorting: true,
    }),
    helper.accessor('status', {
      header: 'Status',
      cell: (info) => {
        const s = info.getValue() || 'draft';
        const style = STATUS_STYLES[s];
        return (
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            padding: '2px 8px', borderRadius: 999, fontSize: 10,
            fontWeight: 600, letterSpacing: 0.3,
            background: style?.bg || '#6b728018',
            color: style?.color || '#6b7280',
            textTransform: 'uppercase', whiteSpace: 'nowrap',
          }}>
            {s.replace(/_/g, ' ')}
          </span>
        );
      },
      enableSorting: true,
    }),
    helper.accessor('created_at', {
      header: 'Submitted',
      cell: (info) => {
        const val = info.getValue();
        return val ? new Date(val).toLocaleDateString() : '-';
      },
      enableSorting: true,
    }),
    helper.accessor('updated_at', {
      header: 'Updated',
      cell: (info) => {
        const val = info.getValue();
        if (!val) return '-';
        const d = new Date(val);
        const now = new Date();
        const diff = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
        return diff === 0 ? 'Today' : diff === 1 ? '1d ago' : `${diff}d ago`;
      },
      enableSorting: true,
    }),
    helper.display({
      id: 'elapsed',
      header: 'Days',
      cell: (info) => elapsedDays(info.row.original.created_at),
      enableSorting: false,
    }),
    helper.accessor('estimated_reward', {
      header: 'Est. Reward',
      cell: (info) => {
        const val = info.getValue() || 0;
        const currency = info.row.original.currency || 'USD';
        return val > 0 ? formatCurrency(val, currency) : '-';
      },
      enableSorting: true,
    }),
    helper.accessor('confirmed_reward', {
      header: 'Reward',
      cell: (info) => {
        const val = info.getValue() || 0;
        const currency = info.row.original.currency || 'USD';
        return val > 0 ? formatCurrency(val, currency) : '-';
      },
      enableSorting: true,
    }),
    helper.accessor('evidence_count', {
      header: 'Evidence',
      cell: (info) => info.getValue() || 0,
      enableSorting: true,
    }),
  ], []);

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Report History</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>
          {total > 0 ? `${total} report${total !== 1 ? 's' : ''} tracked` : 'Track all submitted bug bounty reports'}
        </p>
      </div>

      {stats && (
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
          gap: 10, marginBottom: 20,
        }}>
          <WidgetBox label="Total" value={stats.total} color="#8b5cf6" />
          <WidgetBox label="Triaged" value={stats.status_counts?.triaged ?? 0} color="#22c55e" />
          <WidgetBox label="Paid" value={stats.status_counts?.paid ?? 0} color="#10b981" />
          <WidgetBox label="Pending" value={(stats.status_counts?.draft ?? 0) + (stats.status_counts?.submitted ?? 0)} color="#f97316" />
          <WidgetBox label="Need Info" value={stats.status_counts?.need_more_info ?? 0} color="#eab308" />
          <WidgetBox label="Duplicates" value={stats.status_counts?.duplicate ?? 0} color="#ef4444" />
          <WidgetBox label="Total Rewards" value={`$${(stats.total_rewards || 0).toLocaleString()}`} color="#10b981" />
          <WidgetBox label="Est. Rewards" value={`$${(stats.estimated_rewards || 0).toLocaleString()}`} color="#8b5cf6" />
        </div>
      )}

      <Panel
        title="Reports"
        loading={isLoading}
        empty={!isLoading && items.length === 0}
        emptyMessage="No reports found. Generate your first report from the Report Center."
      >
        <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPagination(prev => ({ ...prev, pageIndex: 0 })); }}
            style={selectStyle}
          >
            <option value="all">All Statuses</option>
            {REPORT_STATUSES.map(s => (
              <option key={s} value={s}>{s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
            ))}
          </select>
        </div>

        <DataTable
          data={items as any}
          columns={columns as any}
          pageSize={pagination.pageSize}
          onRowClick={handleRowClick as any}
          filterable={true}
          manual={true}
          pageCount={Math.ceil(total / pagination.pageSize)}
          total={total}
          sorting={sorting as any}
          pagination={pagination as any}
          onSortingChange={setSorting as any}
          onPaginationChange={setPagination as any}
          onGlobalFilterChange={handleGlobalFilterChange}
        />
      </Panel>
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  background: '#1e2230', border: '1px solid #2a2e3d', borderRadius: 6,
  color: '#e2e4e9', padding: '6px 12px', fontSize: 12, outline: 'none',
  cursor: 'pointer',
};

function WidgetBox({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div style={{
      background: '#1a1d29', borderRadius: 8, border: '1px solid #2a2e3d',
      padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <span style={{ fontSize: 10, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</span>
      <span style={{ fontSize: 18, fontWeight: 700, color }}>{value}</span>
    </div>
  );
}
