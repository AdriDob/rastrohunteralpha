import { useParams, useNavigate } from 'react-router-dom';
import { useReportById, useUpdateReport } from '../lib/query';
import Badge from '../components/ui/Badge';
import Panel from '../components/ui/Panel';
import LoadingState from '../components/ui/LoadingState';
import { REPORT_STATUSES } from '../types';
import { useState } from 'react';

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

function formatCurrency(amount: number, currency: string): string {
  const symbols: Record<string, string> = { USD: '$', EUR: '€', GBP: '£', BTC: '₿', ETH: 'Ξ' };
  const sym = symbols[currency] || currency + ' ';
  return sym + amount.toLocaleString();
}

function elapsedDays(dateStr: string | null): string {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  const diff = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return '0d';
  return diff === 0 ? 'Today' : diff === 1 ? '1d' : `${diff}d`;
}

const sectionStyle: React.CSSProperties = {
  background: '#1a1d29', borderRadius: 8, border: '1px solid #2a2e3d',
  padding: 16, marginBottom: 12,
};

const labelStyle: React.CSSProperties = {
  fontSize: 10, color: '#7c8299', textTransform: 'uppercase',
  letterSpacing: 0.5, marginBottom: 4,
};

const valueStyle: React.CSSProperties = {
  fontSize: 14, color: '#e2e4e9', fontWeight: 500,
};

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const reportId = id ? parseInt(id, 10) : null;
  const { data: report, isLoading, isError } = useReportById(reportId);
  const updateMutation = useUpdateReport();
  const [newStatus, setNewStatus] = useState('');

  const handleStatusChange = (status: string) => {
    if (reportId === null) return;
    setNewStatus(status);
    updateMutation.mutate(
      { id: reportId, data: { status } as Record<string, unknown> },
      { onError: (err) => { console.warn('Status change failed:', err); } },
    );
  };

  if (!reportId) {
    return (
      <Panel title="Invalid Report" empty emptyMessage="No report ID specified.">
        <div />
      </Panel>
    );
  }

  if (isLoading) {
    return <LoadingState count={3} type="card" />;
  }

  if (isError || !report) {
    return (
      <Panel title="Report Not Found" empty emptyMessage="The report could not be found.">
        <div />
      </Panel>
    );
  }

  const timeline = report.timeline || [];
  const attachments = report.attachments || [];
  const content = report.content || {};

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button
          onClick={() => navigate('/reports/history')}
          style={{
            background: '#1e2230', border: '1px solid #2a2e3d', borderRadius: 6,
            color: '#e2e4e9', padding: '6px 12px', cursor: 'pointer', fontSize: 12,
          }}
        >
          &larr; Back
        </button>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>
          Report #{report.id}
        </h1>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          padding: '2px 10px', borderRadius: 999, fontSize: 10,
          fontWeight: 600, letterSpacing: 0.3,
          background: (STATUS_STYLES[report.status]?.bg || '#6b728018'),
          color: (STATUS_STYLES[report.status]?.color || '#6b7280'),
          textTransform: 'uppercase', whiteSpace: 'nowrap',
        }}>
          {report.status.replace(/_/g, ' ')}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 16 }}>
        <div style={sectionStyle}>
          <div style={labelStyle}>Program</div>
          <div style={valueStyle}>{report.program || '-'}</div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Target</div>
          <div style={valueStyle}>{report.target || '-'}</div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Vulnerability</div>
          <div style={valueStyle}>{report.vulnerability || '-'}</div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Severity</div>
          <div><Badge variant="severity" text={report.severity || 'info'} /></div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>CVSS / Score</div>
          <div style={valueStyle}>
            {(content as Record<string, unknown>)?.cvss as string || '-'}
            {(content as Record<string, unknown>)?.severity_score != null
              ? ` (${(content as Record<string, unknown>).severity_score})` : ''}
          </div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Discovery Date</div>
          <div style={valueStyle}>{report.created_at ? new Date(report.created_at).toLocaleDateString() : '-'}</div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Submission Date</div>
          <div style={valueStyle}>{report.created_at ? new Date(report.created_at).toLocaleDateString() : '-'}</div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Last Update</div>
          <div style={valueStyle}>{report.updated_at ? new Date(report.updated_at).toLocaleDateString() : '-'}</div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Days Elapsed</div>
          <div style={valueStyle}>{elapsedDays(report.created_at)}</div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Status</div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <select
              value={newStatus || report.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              style={{
                background: '#1e2230', border: '1px solid #2a2e3d', borderRadius: 6,
                color: '#e2e4e9', padding: '4px 8px', fontSize: 12, outline: 'none',
                cursor: 'pointer',
              }}
            >
              {REPORT_STATUSES.map(s => (
                <option key={s} value={s}>{s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 16 }}>
        <div style={sectionStyle}>
          <div style={labelStyle}>Estimated Reward</div>
          <div style={{ ...valueStyle, color: '#8b5cf6' }}>
            {report.estimated_reward ? formatCurrency(report.estimated_reward, report.currency || 'USD') : '-'}
          </div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Confirmed Reward</div>
          <div style={{ ...valueStyle, color: '#10b981' }}>
            {report.confirmed_reward ? formatCurrency(report.confirmed_reward, report.currency || 'USD') : '-'}
          </div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Currency</div>
          <div style={valueStyle}>{report.currency || 'USD'}</div>
        </div>
        <div style={sectionStyle}>
          <div style={labelStyle}>Evidence Count</div>
          <div style={valueStyle}>{report.evidence_count ?? 0}</div>
        </div>
      </div>

      {report.notes ? (
        <div style={sectionStyle}>
          <div style={labelStyle}>Internal Notes</div>
          <div style={{ ...valueStyle, fontSize: 13, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{report.notes}</div>
        </div>
      ) : null}

      {timeline.length > 0 && (
        <Panel title="Timeline" accent="#8b5cf6">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {timeline.map((entry: Record<string, unknown>, i: number) => (
              <div key={i} style={{
                display: 'flex', gap: 12, alignItems: 'flex-start',
                padding: '8px 0', borderBottom: i < timeline.length - 1 ? '1px solid #2a2e3d' : 'none',
              }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%', marginTop: 6, flexShrink: 0,
                  background: entry.color as string || '#8b5cf6',
                }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, color: '#e2e4e9', fontWeight: 500 }}>
                    {entry.title as string || 'Event'}
                  </div>
                  {!!entry.description && (
                    <div style={{ fontSize: 11, color: '#7c8299', marginTop: 2 }}>{String(entry.description)}</div>
                  )}
                </div>
                {!!entry.date && (
                  <div style={{ fontSize: 10, color: '#6b7280', whiteSpace: 'nowrap' }}>
                    {new Date(String(entry.date)).toLocaleDateString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Panel>
      )}

      {attachments.length > 0 && (
        <Panel title={`Attachments (${attachments.length})`} accent="#f97316">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {attachments.map((att: string, i: number) => (
              <div key={i} style={{
                background: '#1e2230', borderRadius: 6, border: '1px solid #2a2e3d',
                padding: '8px 12px', fontSize: 12, color: '#e2e4e9',
              }}>
                {att}
              </div>
            ))}
          </div>
        </Panel>
      )}

      {report.finding_ids && report.finding_ids.length > 0 && (
        <Panel title={`Linked Findings (${report.finding_ids.length})`} accent="#22c55e">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {report.finding_ids.map((fid: number) => (
              <span key={fid} style={{
                background: '#1e2230', borderRadius: 6, border: '1px solid #2a2e3d',
                padding: '4px 10px', fontSize: 12, color: '#22c55e', cursor: 'pointer',
              }} onClick={() => navigate(`/finding/${fid}`)}>
                Finding #{fid}
              </span>
            ))}
          </div>
        </Panel>
      )}

      {report.content && (
        <Panel title="Report Content" accent="#3b82f6">
          <pre style={{
            background: '#0d0f14', padding: 16, borderRadius: 6,
            border: '1px solid #1e2230', fontSize: 12, color: '#e2e4e9',
            maxHeight: 500, overflow: 'auto', whiteSpace: 'pre-wrap', margin: 0,
          }}>
            {JSON.stringify(report.content, null, 2)}
          </pre>
        </Panel>
      )}
    </div>
  );
}
