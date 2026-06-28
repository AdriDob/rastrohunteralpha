import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useI18n } from '../lib/i18n';
import { tokens } from '../design-system/tokens';

const API = 'http://127.0.0.1:8000/api/agents';

interface StageEntry {
  from_state: string;
  to_state: string;
  agent_id: string;
  status: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

interface PipelineInfo {
  id: string;
  target_id: number;
  target_name: string;
  state: string;
  retries: number;
  quality_score: number;
  stages: StageEntry[];
  error: string;
  created_at: string;
}

const STATE_ORDER = [
  'pending', 'discovery', 'validation', 'evidence', 'ai_review',
  'ready', 'submitted', 'triaged', 'paid', 'closed',
];

const STATE_COLORS: Record<string, string> = {
  pending: '#6b7280',
  discovery: '#3b82f6',
  validation: '#8b5cf6',
  evidence: '#f59e0b',
  ai_review: '#10b981',
  ready: '#22c55e',
  submitted: '#06b6d4',
  triaged: '#f97316',
  paid: '#6366f1',
  closed: '#22c55e',
  failed: '#ef4444',
  cancelled: '#6b7280',
};

function PipelineProgress({ state }: { state: string }) {
  const idx = STATE_ORDER.indexOf(state);
  const progress = idx >= 0 ? ((idx + 1) / STATE_ORDER.length) * 100 : 0;

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: tokens.colors.textMuted }}>Progress</span>
        <span style={{ fontSize: 12, fontWeight: 600, color: tokens.colors.text }}>
          {Math.round(progress)}%
        </span>
      </div>
      <div style={{
        height: 6, borderRadius: 3, background: '#1a1d29', overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', borderRadius: 3,
          background: `linear-gradient(90deg, ${tokens.colors.accent}, ${tokens.colors.accent}bb)`,
          width: `${progress}%`,
          transition: 'width 0.6s cubic-bezier(0.25,0.46,0.45,0.94)',
        }} />
      </div>
      <div style={{ display: 'flex', gap: 2, marginTop: 8, flexWrap: 'wrap' }}>
        {STATE_ORDER.map((s) => {
          const sIdx = STATE_ORDER.indexOf(s);
          const cIdx = STATE_ORDER.indexOf(state);
          const isActive = s === state;
          const isPast = cIdx >= 0 && sIdx < cIdx;
          const isFailed = state === 'failed' || state === 'cancelled';
          return (
            <div key={s} title={s} style={{
              width: 20, height: 6, borderRadius: 2,
              background: isFailed
                ? '#ef4444'
                : isActive
                  ? tokens.colors.accent
                  : isPast
                    ? '#22c55e'
                    : '#2a2e3d',
              transition: `all ${tokens.animation.normal}`,
            }} />
          );
        })}
      </div>
    </div>
  );
}

function StateBadge({ state }: { state: string }) {
  const { t } = useI18n();
  const key = `pipeline_state_${state}` as keyof typeof t;
  const label = t[key] || state;
  return (
    <span style={{
      fontSize: 12, padding: '3px 10px', borderRadius: 6, fontWeight: 600,
      background: `${STATE_COLORS[state] || '#6b7280'}20`,
      color: STATE_COLORS[state] || '#6b7280',
      border: `1px solid ${STATE_COLORS[state] || '#6b7280'}40`,
    }}>
      {label}
    </span>
  );
}

function PipelineCard({
  pipeline, onCancel, onDelete,
}: {
  pipeline: PipelineInfo;
  onCancel: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const isTerminal = ['closed', 'failed', 'cancelled'].includes(pipeline.state);

  return (
    <div style={{
      background: tokens.colors.surface,
      borderRadius: tokens.radius.lg,
      border: `1px solid ${tokens.colors.border}`,
      padding: tokens.spacing.lg,
      cursor: 'pointer',
      transition: `all ${tokens.animation.normal}`,
    }}
      onClick={() => navigate(`/pipeline/${pipeline.id}`)}
      onMouseEnter={(e) => e.currentTarget.style.borderColor = tokens.colors.accent}
      onMouseLeave={(e) => e.currentTarget.style.borderColor = tokens.colors.border}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 600, color: tokens.colors.text, marginBottom: 4 }}>
            {pipeline.target_name || `Target #${pipeline.target_id}`}
          </div>
          <div style={{ fontSize: 11, color: tokens.colors.textMuted, fontFamily: 'monospace' }}>
            {pipeline.id.slice(0, 12)}...
          </div>
        </div>
        <StateBadge state={pipeline.state} />
      </div>

      <PipelineProgress state={pipeline.state} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 11, color: tokens.colors.textMuted, marginBottom: 2 }}>{t.pipeline_quality_score}</div>
          <div style={{
            fontSize: 20, fontWeight: 700,
            color: pipeline.quality_score >= 0.7
              ? '#22c55e'
              : pipeline.quality_score >= 0.4
                ? '#f59e0b'
                : '#ef4444',
          }}>
            {(pipeline.quality_score * 100).toFixed(0)}%
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: tokens.colors.textMuted, marginBottom: 2 }}>{t.pipeline_retry_count}</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: tokens.colors.text }}>
            {pipeline.retries}
          </div>
        </div>
      </div>

      {pipeline.error && (
        <div style={{
          fontSize: 12, color: '#ef4444', padding: '6px 8px',
          background: 'rgba(239,68,68,0.1)', borderRadius: 6, marginBottom: 12,
        }}>
          {pipeline.error}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        {!isTerminal && (
          <button
            onClick={(e) => { e.stopPropagation(); onCancel(pipeline.id); }}
            style={{
              padding: '5px 12px', borderRadius: 6, border: '1px solid #f59e0b',
              background: '#12141f', color: '#f59e0b', fontSize: 11, fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {t.pipeline_cancel}
          </button>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(pipeline.id); }}
          style={{
            padding: '5px 12px', borderRadius: 6, border: '1px solid #ef4444',
            background: '#12141f', color: '#ef4444', fontSize: 11, fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          {t.pipeline_delete}
        </button>
      </div>
    </div>
  );
}

export default function PipelineMonitor() {
  const { t } = useI18n();
  const [pipelines, setPipelines] = useState<PipelineInfo[]>([]);
  const [filter, setFilter] = useState<string>('');

  const fetchPipelines = useCallback(async () => {
    try {
      const url = filter ? `${API}/pipelines?status=${filter}` : `${API}/pipelines`;
      const res = await fetch(url);
      const data = await res.json();
      setPipelines(data.pipelines || []);
    } catch { /* ignore */ }
  }, [filter]);

  useEffect(() => {
    fetchPipelines();
    const interval = setInterval(fetchPipelines, 5000);
    return () => clearInterval(interval);
  }, [fetchPipelines]);

  const handleCancel = async (id: string) => {
    try {
      await fetch(`${API}/pipelines/${id}/cancel`, { method: 'POST' });
      fetchPipelines();
    } catch { /* ignore */ }
  };

  const handleDelete = async (id: string) => {
    try {
      await fetch(`${API}/pipelines/${id}`, { method: 'DELETE' });
      fetchPipelines();
    } catch { /* ignore */ }
  };

  const handleStartPipeline = async () => {
    const targetName = prompt('Target name (domain or IP):');
    if (!targetName) return;
    try {
      await fetch(`${API}/pipeline/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_id: 0, target_name: targetName }),
      });
      setTimeout(fetchPipelines, 1000);
    } catch { /* ignore */ }
  };

  const activePipelines = pipelines.filter(p => !['closed', 'failed', 'cancelled'].includes(p.state));
  const completedPipelines = pipelines.filter(p => ['closed', 'failed', 'cancelled'].includes(p.state));

  const filterOptions = [
    { value: '', label: t.all },
    { value: 'discovery', label: t.pipeline_state_discovery },
    { value: 'validation', label: t.pipeline_state_validation },
    { value: 'evidence', label: t.pipeline_state_evidence },
    { value: 'ai_review', label: t.pipeline_state_ai_review },
    { value: 'ready', label: t.pipeline_state_ready },
    { value: 'submitted', label: t.pipeline_state_submitted },
    { value: 'triaged', label: t.pipeline_state_triaged },
    { value: 'paid', label: t.pipeline_state_paid },
    { value: 'closed', label: t.pipeline_state_closed },
    { value: 'failed', label: t.pipeline_state_failed },
  ];

  return (
    <div style={{ padding: tokens.spacing.xl, maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: tokens.colors.text, margin: 0 }}>
            {t.pipeline_monitor}
          </h1>
          <p style={{ fontSize: 13, color: tokens.colors.textMuted, margin: '4px 0 0' }}>
            {pipelines.length} pipelines | {activePipelines.length} active
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{
              background: '#161a26', border: `1px solid ${tokens.colors.border}`, borderRadius: 6,
              padding: '8px 12px', color: tokens.colors.text, fontSize: 13,
              outline: 'none',
            }}
          >
            {filterOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <button
            onClick={handleStartPipeline}
            style={{
              padding: '8px 20px', borderRadius: 8, border: 'none',
              background: tokens.colors.accent, color: '#fff',
              fontSize: 13, fontWeight: 600, cursor: 'pointer',
              transition: `opacity ${tokens.animation.normal}`,
            }}
          >
            {t.pipeline_start_new}
          </button>
        </div>
      </div>

      {pipelines.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: 60, color: tokens.colors.textMuted,
          background: tokens.colors.surface, borderRadius: tokens.radius.lg,
          border: `1px solid ${tokens.colors.border}`,
        }}>
          <p style={{ fontSize: 14, margin: 0 }}>{t.pipeline_no_pipelines}</p>
          <button
            onClick={handleStartPipeline}
            style={{
              marginTop: 16, padding: '8px 20px', borderRadius: 8, border: 'none',
              background: tokens.colors.accent, color: '#fff',
              fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}
          >
            {t.pipeline_start_new}
          </button>
        </div>
      ) : (
        <>
          {activePipelines.length > 0 && (
            <div style={{ marginBottom: 32 }}>
              <h2 style={{ fontSize: 16, fontWeight: 600, color: tokens.colors.text, marginBottom: 16 }}>
                Active ({activePipelines.length})
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 16 }}>
                {activePipelines.map((p) => (
                  <PipelineCard key={p.id} pipeline={p} onCancel={handleCancel} onDelete={handleDelete} />
                ))}
              </div>
            </div>
          )}

          {completedPipelines.length > 0 && (
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 600, color: tokens.colors.textMuted, marginBottom: 16 }}>
                History ({completedPipelines.length})
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 16 }}>
                {completedPipelines.map((p) => (
                  <PipelineCard key={p.id} pipeline={p} onCancel={handleCancel} onDelete={handleDelete} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
