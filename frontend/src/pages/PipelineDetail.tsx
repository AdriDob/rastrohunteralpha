import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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

interface PipelineDetail {
  target_id: number;
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

export default function PipelineDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [pipeline, setPipeline] = useState<PipelineDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    try {
      const res = await fetch(`${API}/pipelines/${id}`);
      if (!res.ok) { setLoading(false); return; }
      const data = await res.json();
      setPipeline(data.pipeline || null);
    } catch { /* ignore */ }
    setLoading(false);
  }, [id]);

  useEffect(() => {
    fetchDetail();
    const interval = setInterval(fetchDetail, 5000);
    return () => clearInterval(interval);
  }, [fetchDetail]);

  if (!id) return <div>No pipeline ID</div>;

  if (loading) {
    return (
      <div style={{ padding: tokens.spacing.xl, maxWidth: 1000, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', padding: 60, color: tokens.colors.textMuted }}>
          Loading...
        </div>
      </div>
    );
  }

  if (!pipeline) {
    return (
      <div style={{ padding: tokens.spacing.xl, maxWidth: 1000, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', padding: 60, color: tokens.colors.textMuted }}>
          Pipeline not found
        </div>
        <div style={{ textAlign: 'center' }}>
          <button
            onClick={() => navigate('/pipeline-monitor')}
            style={{
              padding: '8px 20px', borderRadius: 8, border: 'none',
              background: tokens.colors.accent, color: '#fff',
              fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Back to Pipeline Monitor
          </button>
        </div>
      </div>
    );
  }

  const stateIndex = STATE_ORDER.indexOf(pipeline.state);
  const progress = stateIndex >= 0 ? ((stateIndex + 1) / STATE_ORDER.length) * 100 : 0;

  return (
    <div style={{ padding: tokens.spacing.xl, maxWidth: 1000, margin: '0 auto' }}>
      <button
        onClick={() => navigate('/pipeline-monitor')}
        style={{
          padding: '6px 14px', borderRadius: 6, border: `1px solid ${tokens.colors.border}`,
          background: tokens.colors.surface, color: tokens.colors.textMuted,
          fontSize: 12, fontWeight: 500, cursor: 'pointer', marginBottom: 20,
        }}
      >
        ← {t.pipeline_monitor}
      </button>

      <div style={{
        background: tokens.colors.surface,
        borderRadius: tokens.radius.lg,
        border: `1px solid ${tokens.colors.border}`,
        padding: tokens.spacing.xl,
        marginBottom: 24,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: tokens.colors.text, margin: 0 }}>
              {t.pipeline_detail}
            </h1>
            <p style={{ fontSize: 12, color: tokens.colors.textMuted, fontFamily: 'monospace', margin: '4px 0 0' }}>
              {id}
            </p>
          </div>
          <span style={{
            fontSize: 13, padding: '4px 14px', borderRadius: 6, fontWeight: 600,
            background: `${STATE_COLORS[pipeline.state] || '#6b7280'}20`,
            color: STATE_COLORS[pipeline.state] || '#6b7280',
            border: `1px solid ${STATE_COLORS[pipeline.state] || '#6b7280'}40`,
          }}>
            {t[`pipeline_state_${pipeline.state}` as keyof typeof t] || pipeline.state}
          </span>
        </div>

        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: tokens.colors.textMuted }}>{t.pipeline_progress}</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: tokens.colors.text }}>
              {Math.round(progress)}%
            </span>
          </div>
          <div style={{
            height: 8, borderRadius: 4, background: '#1a1d29', overflow: 'hidden',
          }}>
            <div style={{
              height: '100%', borderRadius: 4,
              background: `linear-gradient(90deg, ${tokens.colors.accent}, ${tokens.colors.accent}bb)`,
              width: `${progress}%`,
              transition: 'width 0.6s cubic-bezier(0.25,0.46,0.45,0.94)',
            }} />
          </div>
          <div style={{ display: 'flex', gap: 3, marginTop: 10, justifyContent: 'space-between' }}>
            {STATE_ORDER.map((s) => {
              const sIdx = STATE_ORDER.indexOf(s);
              const isActive = s === pipeline.state;
              const isPast = stateIndex >= 0 && sIdx < stateIndex;
              return (
                <div
                  key={s}
                  style={{
                    flex: 1, height: 8, borderRadius: 2,
                    background: isActive
                      ? tokens.colors.accent
                      : isPast
                        ? '#22c55e'
                        : '#2a2e3d',
                    transition: `all ${tokens.animation.normal}`,
                  }}
                  title={s}
                />
              );
            })}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
            {STATE_ORDER.map((s) => (
              <span key={s} style={{
                fontSize: 9, color: tokens.colors.textMuted,
                textAlign: 'center', flex: 1,
              }}>
                {t[`pipeline_state_${s}` as keyof typeof t]?.slice(0, 6) || s.slice(0, 6)}
              </span>
            ))}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
          <div style={{
            background: 'rgba(255,255,255,0.03)', padding: 16, borderRadius: 8,
          }}>
            <div style={{ fontSize: 11, color: tokens.colors.textMuted, marginBottom: 4 }}>
              {t.pipeline_quality_score}
            </div>
            <div style={{
              fontSize: 28, fontWeight: 700,
              color: pipeline.quality_score >= 0.7
                ? '#22c55e'
                : pipeline.quality_score >= 0.4
                  ? '#f59e0b'
                  : '#ef4444',
            }}>
              {(pipeline.quality_score * 100).toFixed(0)}%
            </div>
          </div>
          <div style={{
            background: 'rgba(255,255,255,0.03)', padding: 16, borderRadius: 8,
          }}>
            <div style={{ fontSize: 11, color: tokens.colors.textMuted, marginBottom: 4 }}>
              {t.pipeline_retry_count}
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: tokens.colors.text }}>
              {pipeline.retries}
            </div>
          </div>
          <div style={{
            background: 'rgba(255,255,255,0.03)', padding: 16, borderRadius: 8,
          }}>
            <div style={{ fontSize: 11, color: tokens.colors.textMuted, marginBottom: 4 }}>
              Stages Completed
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: tokens.colors.text }}>
              {pipeline.stages?.filter((s) => s.status === 'completed').length || 0}
            </div>
          </div>
        </div>

        {pipeline.error && (
          <div style={{
            padding: 12, borderRadius: 8, background: 'rgba(239,68,68,0.1)',
            border: '1px solid rgba(239,68,68,0.2)', marginBottom: 20,
          }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#ef4444', marginBottom: 4 }}>Error</div>
            <div style={{ fontSize: 13, color: '#fca5a5' }}>{pipeline.error}</div>
          </div>
        )}
      </div>

      {/* Transition History */}
      <div style={{
        background: tokens.colors.surface,
        borderRadius: tokens.radius.lg,
        border: `1px solid ${tokens.colors.border}`,
        padding: tokens.spacing.xl,
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, color: tokens.colors.text, margin: '0 0 16px' }}>
          {t.pipeline_transition_history}
        </h2>

        {!pipeline.stages || pipeline.stages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 32, color: tokens.colors.textMuted }}>
            No transitions recorded yet
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {pipeline.stages.map((entry, idx) => (
              <div key={idx} style={{
                display: 'grid',
                gridTemplateColumns: '100px 30px 100px 100px 140px 1fr',
                gap: 8, alignItems: 'center',
                padding: '8px 12px',
                borderRadius: 6,
                background: entry.status === 'failed'
                  ? 'rgba(239,68,68,0.08)'
                  : entry.status === 'cancelled'
                    ? 'rgba(107,114,128,0.08)'
                    : 'rgba(255,255,255,0.02)',
                fontSize: 12,
              }}>
                <span style={{ color: STATE_COLORS[entry.from_state] || tokens.colors.textMuted, fontWeight: 500 }}>
                  {entry.from_state || '-'}
                </span>
                <span style={{ color: tokens.colors.textMuted, textAlign: 'center' }}>→</span>
                <span style={{ color: STATE_COLORS[entry.to_state] || tokens.colors.accent, fontWeight: 600 }}>
                  {entry.to_state}
                </span>
                <span style={{
                  padding: '1px 8px', borderRadius: 4, fontSize: 11, fontWeight: 500,
                  background: entry.status === 'completed'
                    ? 'rgba(34,197,94,0.15)'
                    : entry.status === 'failed'
                      ? 'rgba(239,68,68,0.15)'
                      : 'rgba(107,114,128,0.15)',
                  color: entry.status === 'completed'
                    ? '#22c55e'
                    : entry.status === 'failed'
                      ? '#ef4444'
                      : '#6b7280',
                  textAlign: 'center',
                }}>
                  {entry.status}
                </span>
                <span style={{ color: tokens.colors.textMuted, fontSize: 11 }}>
                  {entry.agent_id || '-'}
                </span>
                <span style={{ color: tokens.colors.textMuted, fontSize: 11, fontFamily: 'monospace' }}>
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
