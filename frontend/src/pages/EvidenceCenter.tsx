import { useState } from 'react';
import { useEvidence } from '../lib/query';
import { createColumnHelper } from '@tanstack/react-table';
import DataTable from '../components/tables/DataTable';
import type { Evidence, PaginationState } from '../types';

const helper = createColumnHelper<Evidence>();
const columns = [
  helper.accessor('id', { header: 'ID' }),
  helper.accessor('attempt_label', { header: 'Attempt' }),
  helper.accessor('request_url', { header: 'URL', cell: (c) => {
    const url = c.getValue();
    return url.length > 50 ? url.slice(0, 50) + '…' : url;
  }}),
  helper.accessor('request_method', { header: 'Method' }),
  helper.accessor('response_status', { header: 'Status' }),
  helper.accessor('consistent', { header: 'Consistent', cell: (c) => (c.getValue() ? '✓' : '✗') }),
  helper.accessor('body_diff_ratio', { header: 'Body Diff', cell: (c) => (c.getValue() * 100).toFixed(1) + '%' }),
];

export default function EvidenceCenter() {
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 20 });
  const { data: res } = useEvidence(null, {
    skip: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
  });
  const [expanded, setExpanded] = useState<Record<number, string>>({});

  const items = res?.items ?? [];
  const total = res?.total ?? 0;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Evidence Center</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>Review captured request/response evidence</p>
      </div>

      {total === 0 && (
        <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: 32, textAlign: 'center' }}>
          <p style={{ color: '#7c8299', fontSize: 14 }}>No evidence records yet. Validate findings to generate evidence.</p>
        </div>
      )}

      <DataTable
        data={items as any}
        columns={columns as any}
        pageSize={20}
        manual
        pageCount={Math.ceil(total / pagination.pageSize)}
        total={total}
        pagination={pagination as any}
        onPaginationChange={setPagination as any}
        onRowClick={(row) => {
          const ev = row as any;
          const id = ev.id;
          setExpanded((prev) => {
            if (prev[id]) {
              const next = { ...prev };
              delete next[id];
              return next;
            }
            return { ...prev, [id]: `curl ${ev.curl_command || ev.request_url}` };
          });
        }}
      />

      {Object.entries(expanded).length > 0 && (
        <div style={{ marginTop: 20 }}>
          {Object.entries(expanded).map(([id, text]) => (
            <div key={id} style={{ background: '#0d0f14', borderRadius: 6, border: '1px solid #1e2230', padding: 16, marginBottom: 8 }}>
              <h4 style={{ margin: '0 0 8px', fontSize: 13, color: '#7c8299' }}>Evidence #{id}</h4>
              <pre style={{ margin: 0, fontSize: 11, color: '#e2e4e9', whiteSpace: 'pre-wrap' }}>{text}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
