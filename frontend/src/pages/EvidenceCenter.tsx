import { useState } from 'react';
import { useEvidence } from '../lib/query';
import { createColumnHelper } from '@tanstack/react-table';
import DataTable from '../components/tables/DataTable';
import FavoriteButton from '../components/FavoriteButton';
import type { Evidence, PaginationState } from '../types';

const helper = createColumnHelper<Evidence>();
const bodyDiffCell = (c: { getValue: () => unknown }) => {
  const ratio = Number(c.getValue());
  const pctVal = Math.min(ratio * 100, 100);
  const pctStr = pctVal.toFixed(1);
  const color = ratio > 0.3 ? '#f97316' : ratio > 0.1 ? '#eab308' : '#6b7280';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 50, height: 4, background: '#0d0f14', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${pctVal}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 11, color }}>{pctStr}%</span>
    </div>
  );
};
const columns = [
  helper.display({ id: 'fav', header: '', cell: (c) => (
    <FavoriteButton itemType="evidence" itemId={(c.row.original as Evidence).id} />
  ), meta: { width: 40 } }),
  helper.accessor('id', { header: 'ID' }),
  helper.accessor('attempt_label', { header: 'Attempt' }),
  helper.accessor('request_url', { header: 'URL', cell: (c) => {
    const url = c.getValue();
    return url.length > 50 ? url.slice(0, 50) + '…' : url;
  }}),
  helper.accessor('request_method', { header: 'Method' }),
  helper.accessor('response_status', { header: 'Status' }),
  helper.accessor('consistent', { header: 'Consistent', cell: (c) => (c.getValue() ? '✓' : '✗') }),
  helper.accessor('body_diff_ratio', { header: 'Body Diff', cell: bodyDiffCell }),
];

function tryParseJson(raw: string | null): string | null {
  if (!raw) return null;
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

function EvidenceExpanded({ ev }: { ev: Evidence }) {
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          <h5 style={{ margin: '0 0 6px', fontSize: 11, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5 }}>Request</h5>
          <pre style={codeBlockStyle}>
            {ev.request_method} {ev.request_url}
            {ev.request_headers ? `\n${tryParseJson(ev.request_headers)}` : ''}
            {ev.request_body ? `\n\n${tryParseJson(ev.request_body)}` : ''}
          </pre>
        </div>
        <div>
          <h5 style={{ margin: '0 0 6px', fontSize: 11, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Response ({ev.response_status})
          </h5>
          <pre style={codeBlockStyle}>
            {ev.response_headers ? `${tryParseJson(ev.response_headers)}\n` : ''}
            {ev.response_body ? tryParseJson(ev.response_body) : '(empty)'}
          </pre>
        </div>
      </div>
      {ev.curl_command && (
        <div style={{ marginTop: 8 }}>
          <h5 style={{ margin: '0 0 4px', fontSize: 11, color: '#7c8299' }}>cURL</h5>
          <pre style={{ ...codeBlockStyle, fontSize: 10 }}>{ev.curl_command}</pre>
        </div>
      )}
    </div>
  );
}

const codeBlockStyle: React.CSSProperties = {
  margin: 0, padding: 12, background: '#0d0f14', borderRadius: 6,
  border: '1px solid #1e2230', fontSize: 11, color: '#e2e4e9',
  whiteSpace: 'pre-wrap', maxHeight: 300, overflow: 'auto',
};

export default function EvidenceCenter() {
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 20 });
  const { data: res } = useEvidence(null, {
    skip: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
  });
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

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
          setExpanded((prev) => {
            const next = { ...prev };
            if (next[ev.id]) delete next[ev.id];
            else next[ev.id] = true;
            return next;
          });
        }}
      />

      {Object.keys(expanded).length > 0 && (
        <div style={{ marginTop: 20 }}>
          {Object.entries(expanded).filter(([, v]) => v).map(([id]) => {
            const ev = items.find((e) => e.id === Number(id));
            if (!ev) return null;
            return (
              <div key={id} style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: 16, marginBottom: 8 }}>
                <h4 style={{ margin: 0, fontSize: 13, color: '#7c8299' }}>
                  Evidence #{id} — {ev.attempt_label}
                  <span style={{ marginLeft: 8, fontSize: 10, color: '#4a4f63' }}>
                    body_diff: {(ev.body_diff_ratio * 100).toFixed(1)}%
                  </span>
                </h4>
                <EvidenceExpanded ev={ev} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
