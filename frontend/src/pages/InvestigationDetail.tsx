import { useParams, useNavigate } from 'react-router-dom';
import { useInvestigationDashboard, useDeleteInvestigation, useUpdateInvestigation } from '../lib/query';
import Panel from '../components/ui/Panel';
import { useQueryClient } from '@tanstack/react-query';

const statusColors: Record<string, string> = {
  active: '#7c3aed',
  paused: '#f59e0b',
  completed: '#10b981',
  abandoned: '#ef4444',
};

const stageConfig: Record<string, { label: string; color: string; icon: string }> = {
  recon: { label: 'Recon', color: '#3b82f6', icon: '🔍' },
  hypotheses: { label: 'Hypotheses', color: '#a855f7', icon: '⟐' },
  validation: { label: 'Validation', color: '#f59e0b', icon: '✓' },
  evidence: { label: 'Evidence', color: '#f97316', icon: '📋' },
  report: { label: 'Report', color: '#10b981', icon: '📄' },
};

function StageBar({ stage, count, maxCount }: { stage: string; count: number; maxCount: number }) {
  const cfg = stageConfig[stage] || { label: stage, color: '#6b7280', icon: '○' };
  const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 14 }}>{cfg.icon}</span>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#7c8299', marginBottom: 2 }}>
          <span>{cfg.label}</span>
          <span>{count}</span>
        </div>
        <div style={{ height: 6, background: '#0d0f14', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: cfg.color, borderRadius: 3, transition: 'width 0.4s' }} />
        </div>
      </div>
    </div>
  );
}

export default function InvestigationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const invId = id ? parseInt(id) : null;
  const { data: dash, isLoading } = useInvestigationDashboard(invId);
  const deleteMutation = useDeleteInvestigation();
  const updateMutation = useUpdateInvestigation();

  if (isLoading) return <p style={{ color: '#7c8299' }}>Loading…</p>;
  if (!dash) return <p style={{ color: '#ef4444' }}>Investigation not found</p>;

  const { investigation: inv, stats, pipeline: pipe } = dash;
  const statusColor = statusColors[inv.status] || '#7c8299';
  const maxStageCount = Math.max(1, ...Object.values(pipe?.stages ?? {}));

  const handleDelete = () => {
    if (!confirm('Delete this investigation?')) return;
    deleteMutation.mutate(inv.id, {
      onSuccess: () => navigate('/investigations'),
    });
  };

  const handleStatusChange = () => {
    const nextStatus = inv.status === 'active' ? 'paused' : inv.status === 'paused' ? 'active' : 'completed';
    updateMutation.mutate(
      { id: inv.id, payload: { status: nextStatus } },
      { onSuccess: () => queryClient.invalidateQueries({ queryKey: ['investigationDashboard', invId] }) },
    );
  };

  return (
    <div>
      <button onClick={() => navigate('/investigations')} style={{
        background: 'none', border: 'none', color: '#7c3aed', cursor: 'pointer',
        fontSize: 13, padding: 0, marginBottom: 16, display: 'inline-block',
      }}>← Back to Investigations</button>

      {/* Header */}
      <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: 20, marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 12, height: 12, borderRadius: '50%', background: statusColor,
              boxShadow: `0 0 6px ${statusColor}80`, flexShrink: 0,
            }} />
            <div>
              <h2 style={{ margin: 0, fontSize: 18, color: '#fff' }}>{inv.name}</h2>
              <span style={{ fontSize: 12, color: '#7c8299' }}>Target #{inv.target_id}</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={handleStatusChange} style={{
              background: '#7c3aed', border: 'none', color: '#fff', padding: '6px 16px',
              borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 500,
            }}>
              {inv.status === 'active' ? 'Pause' : inv.status === 'paused' ? 'Resume' : 'Reopen'}
            </button>
            <button onClick={handleDelete} style={{
              background: 'none', border: '1px solid #ef4444', color: '#ef4444',
              padding: '6px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
            }}>Delete</button>
          </div>
        </div>
        <div style={{ marginTop: 16, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <span style={{
            fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
            color: statusColor, background: `${statusColor}15`,
            padding: '3px 10px', borderRadius: 10,
          }}>{inv.status}</span>
          {inv.tags?.map((t: string) => (
            <span key={t} style={{
              fontSize: 10, color: '#7c8299', background: '#2a2e3d',
              padding: '3px 10px', borderRadius: 10,
            }}>{t}</span>
          ))}
        </div>
        {inv.notes && (
          <p style={{ margin: '12px 0 0', fontSize: 13, color: '#c4c7d0' }}>{inv.notes}</p>
        )}

        {/* Cross-navigation quick actions */}
        <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <QuickNavBtn label="View Pipeline" icon="▤" onClick={() => navigate(`/pipeline?investigationId=${inv.id}`)} />
          <QuickNavBtn label="Generate Hypotheses" icon="⟐" onClick={() => navigate(`/hypothesis?targetId=${inv.target_id}`)} />
          <QuickNavBtn label="View Evidence" icon="📋" onClick={() => navigate(`/evidence?investigationId=${inv.id}`)} />
          <QuickNavBtn label="Generate Report" icon="📄" onClick={() => navigate(`/reports?investigationId=${inv.id}`)} />
        </div>
      </div>

      {/* Stats KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10, marginBottom: 20 }}>
        {[
          { label: 'Endpoints', value: stats.endpoints, color: '#7c3aed' },
          { label: 'Findings', value: stats.findings, color: '#f59e0b' },
          { label: 'Verdicts', value: stats.verdicts, color: '#3b82f6' },
          { label: 'Confirmed', value: stats.confirmed_verdicts, color: '#10b981' },
        ].map(s => (
          <div key={s.label} style={{
            background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d',
            padding: 14, textAlign: 'center',
          }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 10, color: '#7c8299', textTransform: 'uppercase', marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
        {/* Progress KPIs */}
        <div style={{
          background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d',
          padding: 14, textAlign: 'center',
        }}>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#a855f7' }}>{pipe?.progress_pct ?? 0}%</div>
          <div style={{ fontSize: 10, color: '#7c8299', textTransform: 'uppercase', marginTop: 4 }}>Pipeline</div>
        </div>
        <div style={{
          background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d',
          padding: 14, textAlign: 'center',
        }}>
          <div style={{ fontSize: 24, fontWeight: 700, color: pipe?.overall_confidence && pipe.overall_confidence > 0.7 ? '#10b981' : pipe?.overall_confidence && pipe.overall_confidence > 0.3 ? '#f59e0b' : '#ef4444' }}>
            {pipe?.overall_confidence != null ? `${(pipe.overall_confidence * 100).toFixed(0)}%` : 'N/A'}
          </div>
          <div style={{ fontSize: 10, color: '#7c8299', textTransform: 'uppercase', marginTop: 4 }}>Confidence</div>
        </div>
      </div>

      {/* Pipeline Progress Visualization */}
      {pipe && (
        <Panel title="Pipeline Progress" subtitle={`${pipe.progress_pct}% complete · ${pipe.timeline.filter(t => t.status === 'done').length}/${pipe.timeline.length} stages`} accent="#a855f7" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {/* Progress bar */}
            <div style={{ height: 8, background: '#0d0f14', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{
                width: `${pipe.progress_pct}%`, height: '100%',
                background: 'linear-gradient(90deg, #7c3aed, #a855f7)',
                borderRadius: 4, transition: 'width 0.6s ease',
              }} />
            </div>
            {/* Stage bars */}
            {Object.entries(stageConfig).map(([key]) => {
              const count = (pipe.stages as Record<string, number>)[key] ?? 0;
              return <StageBar key={key} stage={key} count={count} maxCount={maxStageCount} />;
            })}
          </div>
        </Panel>
      )}

      {/* Timeline */}
      {pipe && pipe.timeline.length > 0 && (
        <Panel title="Investigation Timeline" subtitle="Key events in this investigation" accent="#8b5cf6" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {pipe.timeline.map((event, i) => {
              const cfg = stageConfig[event.stage] || { label: event.stage, color: '#6b7280', icon: '○' };
              const isDone = event.status === 'done';
              return (
                <div key={i} style={{
                  display: 'flex', gap: 10, alignItems: 'flex-start',
                  padding: '8px 0', borderBottom: i < pipe.timeline.length - 1 ? '1px solid #2a2e3d' : undefined,
                  opacity: isDone ? 1 : 0.5,
                }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: isDone ? cfg.color : '#4a4f63',
                    marginTop: 4, flexShrink: 0,
                    boxShadow: isDone ? `0 0 6px ${cfg.color}80` : undefined,
                  }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, color: isDone ? '#e2e4e9' : '#4a4f63' }}>
                      <span style={{ fontWeight: 600 }}>{cfg.label}:</span> {event.label}
                    </div>
                    {event.timestamp && (
                      <div style={{ fontSize: 10, color: '#7c8299', marginTop: 2 }}>
                        {new Date(event.timestamp).toLocaleString()}
                      </div>
                    )}
                  </div>
                  <span style={{
                    fontSize: 10, padding: '2px 8px', borderRadius: 6,
                    background: isDone ? `${cfg.color}15` : '#1a1d29',
                    color: isDone ? cfg.color : '#4a4f63',
                    fontWeight: 600, textTransform: 'uppercase',
                  }}>
                    {isDone ? 'Done' : 'Pending'}
                  </span>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      {/* Findings by Severity */}
      {stats.findings_by_severity && Object.keys(stats.findings_by_severity).length > 0 && (
        <Panel title="Findings by Severity">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.entries(stats.findings_by_severity).map(([sev, count]) => {
              const sevColor = sev === 'critical' ? '#ef4444' : sev === 'high' ? '#f59e0b' : sev === 'medium' ? '#3b82f6' : '#7c8299';
              return (
                <div key={sev} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', color: sevColor, width: 70 }}>{sev}</span>
                  <div style={{ flex: 1, height: 8, background: '#2a2e3d', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{
                      width: `${(count as number) / Math.max(...Object.values(stats.findings_by_severity) as number[]) * 100}%`,
                      height: '100%', background: sevColor, borderRadius: 4,
                    }} />
                  </div>
                  <span style={{ fontSize: 12, color: '#e2e4e9', fontWeight: 600, width: 30, textAlign: 'right' }}>{count as number}</span>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      {/* Empty state when no data */}
      {stats.endpoints === 0 && stats.findings === 0 && (
        <div style={{ textAlign: 'center', padding: 40, color: '#7c8299', background: '#1a1d29', borderRadius: 8, border: '1px solid #2a2e3d' }}>
          <div style={{ fontSize: 28, marginBottom: 12 }}>🔍</div>
          <p style={{ fontSize: 14, margin: 0 }}>This investigation has no data yet.</p>
          <p style={{ fontSize: 12, margin: '8px 0 0', color: '#4a4f63' }}>
            Use the quick actions above to generate hypotheses or view the target pipeline.
          </p>
        </div>
      )}
    </div>
  );
}

function QuickNavBtn({ label, icon, onClick }: { label: string; icon: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '6px 12px', borderRadius: 6, border: '1px solid #2a2e3d',
        background: '#12141f', color: '#c4c7d0', fontSize: 11, fontWeight: 600,
        cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
        transition: 'all 0.12s',
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = '#7c3aed'; e.currentTarget.style.background = '#1e2230'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2e3d'; e.currentTarget.style.background = '#12141f'; }}
    >
      <span>{icon}</span>
      <span>{label}</span>
    </button>
  );
}
