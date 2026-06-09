import { useState, useCallback } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
} from '@tanstack/react-table';
import type { ColumnDef, SortingState as TanStackSortingState, PaginationState } from '@tanstack/react-table';

interface DataTableProps<T extends Record<string, unknown>> {
  data: T[];
  columns: ColumnDef<T, any>[];
  pageSize?: number;
  onRowClick?: (row: T) => void;
  filterable?: boolean;
  /** Enable server-driven pagination/sorting */
  manual?: boolean;
  pageCount?: number;
  total?: number;
  onPaginationChange?: (pagination: PaginationState) => void;
  onSortingChange?: (sorting: TanStackSortingState) => void;
  sorting?: TanStackSortingState;
  pagination?: PaginationState;
  onGlobalFilterChange?: (value: string) => void;
}

export default function DataTable<T extends Record<string, unknown>>({
  data, columns, pageSize = 10, onRowClick, filterable = true,
  manual = false, pageCount, total, onPaginationChange, onSortingChange,
  sorting: externalSorting, pagination: externalPagination,
  onGlobalFilterChange,
}: DataTableProps<T>) {
  const [internalSorting, setInternalSorting] = useState<TanStackSortingState>([]);
  const [internalPagination, setInternalPagination] = useState<PaginationState>({ pageIndex: 0, pageSize });
  const [internalFilter, setInternalFilter] = useState('');

  const sorting = manual ? (externalSorting ?? []) : internalSorting;
  const pagination = manual ? (externalPagination ?? { pageIndex: 0, pageSize }) : internalPagination;

  const handleSortingChange = useCallback((updater: TanStackSortingState | ((old: TanStackSortingState) => TanStackSortingState)) => {
    const next = typeof updater === 'function' ? updater(sorting) : updater;
    if (manual) {
      onSortingChange?.(next);
    } else {
      setInternalSorting(next);
    }
  }, [manual, onSortingChange, sorting]);

  const handlePaginationChange = useCallback((updater: PaginationState | ((old: PaginationState) => PaginationState)) => {
    const next = typeof updater === 'function' ? updater(pagination) : updater;
    if (manual) {
      onPaginationChange?.(next);
    } else {
      setInternalPagination(next);
    }
  }, [manual, onPaginationChange, pagination]);

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      pagination,
      globalFilter: internalFilter,
    },
    onSortingChange: handleSortingChange,
    onPaginationChange: handlePaginationChange,
    onGlobalFilterChange: (v) => {
      setInternalFilter(v);
      onGlobalFilterChange?.(v);
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: manual ? undefined : getSortedRowModel(),
    getFilteredRowModel: manual ? undefined : getFilteredRowModel(),
    getPaginationRowModel: manual ? undefined : getPaginationRowModel(),
    pageCount: manual ? pageCount : undefined,
    manualPagination: manual,
    manualSorting: manual,
  });

  const cellStyle: React.CSSProperties = {
    padding: '8px 12px', fontSize: 12, borderBottom: '1px solid #2a2e3d',
    color: '#c4c7d0', whiteSpace: 'nowrap',
  };
  const headerStyle: React.CSSProperties = {
    ...cellStyle, fontWeight: 600, color: '#7c8299',
    fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5,
    borderBottom: '2px solid #2a2e3d', cursor: 'pointer',
    userSelect: 'none', background: '#161a26',
  };
  const inputStyle: React.CSSProperties = {
    background: '#161a26', border: '1px solid #2a2e3d', borderRadius: 6,
    padding: '8px 14px', color: '#e2e4e9', fontSize: 13, width: 240,
    outline: 'none', marginBottom: 12,
  };

  const displayPageCount = manual ? (pageCount ?? 1) : table.getPageCount();
  const displayTotal = total ?? data.length;

  return (
    <div>
      {filterable && (
        <input
          placeholder="Filter…"
          value={internalFilter}
          onChange={(e) => {
            const v = e.target.value;
            setInternalFilter(v);
            onGlobalFilterChange?.(v);
          }}
          style={inputStyle}
        />
      )}
      <div style={{ overflowX: 'auto', borderRadius: 8, border: '1px solid #2a2e3d', background: '#1a1d29' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    onClick={h.column.getToggleSortingHandler()}
                    style={headerStyle}
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {{ asc: ' ↑', desc: ' ↓' }[h.column.getIsSorted() as string] ?? ''}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                onClick={() => onRowClick?.(row.original)}
                style={{ cursor: onRowClick ? 'pointer' : undefined, transition: 'background 0.1s' }}
                onMouseEnter={(e) => { e.currentTarget.style.background = '#222639'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = ''; }}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} style={cellStyle}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
        <span style={{ fontSize: 12, color: '#7c8299' }}>
          {manual
            ? `Page ${pagination.pageIndex + 1} of ${displayPageCount} (${displayTotal} total)`
            : `Page ${table.getState().pagination.pageIndex + 1} of ${displayPageCount}`
          }
        </span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => table.setPageIndex(0)} disabled={!table.getCanPreviousPage()}
            style={btnStyle}>«</button>
          <button onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}
            style={btnStyle}>‹</button>
          <button onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}
            style={btnStyle}>›</button>
          <button onClick={() => table.setPageIndex(table.getPageCount() - 1)} disabled={!table.getCanNextPage()}
            style={btnStyle}>»</button>
        </div>
      </div>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  background: '#1e2230', border: '1px solid #2a2e3d', borderRadius: 4,
  color: '#e2e4e9', padding: '4px 10px', cursor: 'pointer', fontSize: 13,
};
