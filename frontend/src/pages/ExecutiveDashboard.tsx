import { useState, useEffect } from 'react';
import { useI18n } from '../lib/i18n';
import { tokens } from '../design-system/tokens';

const API = 'http://127.0.0.1:8000/api/agents';

interface AgentHealth {
  agent_id: string;
  name: string;
  status: string;
  tasks_completed: number;
  tasks_failed: number;
  running: boolean;
}

interface PipelineInfo {
  target_id?: number;
  target_name?: string;
  state?: string;
  retries?: number;
  started_at?: string;
}

interface FinancialSummary {
  metrics?: Record<string, number>;
  goals?: Array<{ name: string; progress_pct: number; target_amount: number; current_amount: number }>;
}

const STATUS_PING: Record<string, string> = {
  idle: '#22c55e',
  working: '#3b82f6',
  waiting: '#eab308',
  error: '#ef4444',
  offline: '#6b7280',
};

function KPIWidget({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div style={{
      background: tokens.colors.surface,
      borderRadius: tokens.radius.lg,
      border: `1px solid ${accent ? 'rgba(250,204,21,0.3)' : tokens.colors.border}`,
      padding: tokens.spacing.lg,
      transition: `all ${tokens.animation.normal}`,
    }}>
      <div style={{ fontSize: 12, color: tokens.colors.textMuted, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: accent ? '#eab308' : tokens.colors.text }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: tokens.colors.textMuted, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function AgentHealthBar() {
  const { t } = useI18n();
  const [agents, setAgents] = useState<AgentHealth[]>([]);

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await window.fetch(`${API}/health`);
        const data = await res.json();
        setAgents(Object.values(data.agents || {}) as AgentHealth[]);
      } catch { /* ignore */ }
    };
    fetch();
    const interval = setInterval(fetch, 5000);
    return () => clearInterval(interval);
  }, []);

  const working = agents.filter(a => a.status === 'working').length;
  const healthy = agents.filter(a => a.status === 'idle').length;
  const errored = agents.filter(a => a.status === 'error').length;

  return (
    <div style={{
      background: tokens.colors.surface,
      borderRadius: tokens.radius.lg,
      border: `1px solid ${tokens.colors.border}`,
      padding: tokens.spacing.lg,
    }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: tokens.colors.text, margin: '0 0 16px' }}>
        {t.dashboard_agent_health}
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        <MiniStat label={t.dashboard_agents_online} value={String(agents.filter(a => a.running).length)} color="#22c55e" />
        <MiniStat label={t.agent_working} value={String(working)} color="#3b82f6" />
        <MiniStat label={t.agent_idle} value={String(healthy)} color="#6b7280" />
        <MiniStat label={t.agent_error} value={String(errored)} color="#ef4444" />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {agents.map((a) => (
          <div key={a.agent_id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: STATUS_PING[a.status] || '#6b7280',
              boxShadow: `0 0 4px ${STATUS_PING[a.status] || '#6b7280'}`,
            }} />
            <span style={{ color: tokens.colors.text, flex: 1 }}>{a.name}</span>
            <span style={{ color: tokens.colors.textMuted, fontSize: 11 }}>
              {a.tasks_completed} ok / {a.tasks_failed} err
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MiniStat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color: tokens.colors.textMuted }}>{label}</div>
    </div>
  );
}

function PipelineOverview() {
  const { t } = useI18n();
  const [pipelines, setPipelines] = useState<Record<string, PipelineInfo>>({});

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await window.fetch(`${API}/coordinator/pipelines`);
        const data = await res.json();
        setPipelines(data.pipelines || {});
      } catch { /* ignore */ }
    };
    fetch();
    const interval = setInterval(fetch, 5000);
    return () => clearInterval(interval);
  }, []);

  const entries = Object.entries(pipelines);
  const active = entries.filter(([, i]) => i.state !== 'completed' && i.state !== 'failed').length;
  const completed = entries.filter(([, i]) => i.state === 'completed').length;

  return (
    <div style={{
      background: tokens.colors.surface,
      borderRadius: tokens.radius.lg,
      border: `1px solid ${tokens.colors.border}`,
      padding: tokens.spacing.lg,
    }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: tokens.colors.text, margin: '0 0 16px' }}>
        {t.dashboard_pipeline_overview}
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        <MiniStat label={t.dashboard_active_pipelines} value={String(active)} color="#3b82f6" />
        <MiniStat label={t.dashboard_completed_today} value={String(completed)} color="#22c55e" />
      </div>
      {entries.length === 0 && (
        <div style={{ color: tokens.colors.textMuted, fontSize: 13, textAlign: 'center', padding: 16 }}>
          No pipelines yet
        </div>
      )}
      {entries.slice(0, 5).map(([pid, info]) => (
        <div key={pid} style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          fontSize: 12,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: info.state === 'completed' ? '#22c55e' : info.state === 'failed' ? '#ef4444' : '#3b82f6',
          }} />
          <span style={{ color: tokens.colors.text, flex: 1 }}>{info.target_name || '?'}</span>
          <span style={{ color: tokens.colors.textMuted }}>{info.state}</span>
        </div>
      ))}
    </div>
  );
}

function FinancialPreview() {
  const { t } = useI18n();
  const [summary, setSummary] = useState<FinancialSummary | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await window.fetch(`${API}/financial/summary`);
        const data = await res.json();
        setSummary(data);
      } catch { /* ignore */ }
    };
    fetch();
    const interval = setInterval(fetch, 15000);
    return () => clearInterval(interval);
  }, []);

  const metrics = summary?.metrics || {};
  const goals = summary?.goals || [];

  return (
    <div style={{
      background: tokens.colors.surface,
      borderRadius: tokens.radius.lg,
      border: `1px solid ${tokens.colors.border}`,
      padding: tokens.spacing.lg,
    }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: tokens.colors.text, margin: '0 0 16px' }}>
        {t.dashboard_financial_preview}
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 11, color: tokens.colors.textMuted }}>{t.total_revenue}</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#22c55e' }}>
            ${(metrics.total_paid || 0).toFixed(0)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: tokens.colors.textMuted }}>{t.pending_rewards}</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#eab308' }}>
            ${(metrics.pending_revenue || 0).toFixed(0)}
          </div>
        </div>
      </div>
      {goals.length > 0 && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: tokens.colors.textMuted, marginBottom: 8 }}>
            {t.goals}
          </div>
          {goals.slice(0, 3).map((g, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: tokens.colors.text }}>{g.name}</span>
                <span style={{ color: tokens.colors.textMuted }}>
                  ${g.current_amount.toFixed(0)} / ${g.target_amount.toFixed(0)}
                </span>
              </div>
              <div style={{
                height: 4, background: 'rgba(255,255,255,0.1)', borderRadius: 2, overflow: 'hidden',
              }}>
                <div style={{
                  width: `${Math.min(g.progress_pct, 100)}%`, height: '100%',
                  background: 'linear-gradient(90deg, #3b82f6, #eab308)',
                  borderRadius: 2, transition: 'width 1s ease',
                }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ExecutiveDashboard() {
  const { t } = useI18n();

  return (
    <div style={{ padding: tokens.spacing.xl, maxWidth: 1400, margin: '0 auto' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: tokens.colors.text, margin: '0 0 24px' }}>
        {t.executive_dashboard}
      </h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        <KPIWidget label={t.dashboard_agents_online} value="- / 8" sub={t.dashboard_last_24h} />
        <KPIWidget label={t.dashboard_active_pipelines} value="0" sub={t.dashboard_last_24h} />
        <KPIWidget label={t.dashboard_reports_ready} value="0" sub={t.dashboard_last_24h} />
        <KPIWidget label={t.total_revenue} value="$0" sub={t.dashboard_pending_revenue} accent />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        <AgentHealthBar />
        <PipelineOverview />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <FinancialPreview />
        <div style={{
          background: tokens.colors.surface,
          borderRadius: tokens.radius.lg,
          border: `1px solid ${tokens.colors.border}`,
          padding: tokens.spacing.lg,
        }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: tokens.colors.text, margin: '0 0 16px' }}>
            {t.dashboard_system_activity}
          </h3>
          <div style={{ color: tokens.colors.textMuted, fontSize: 13 }}>
            {t.dashboard_last_24h}
          </div>
        </div>
      </div>
    </div>
  );
}
