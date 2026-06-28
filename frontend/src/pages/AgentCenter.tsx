import { useState, useEffect, useRef, useCallback } from 'react';
import { useI18n } from '../lib/i18n';
import { tokens } from '../design-system/tokens';

const API = 'http://127.0.0.1:8000/api/agents';

interface AgentHealth {
  agent_id: string;
  name: string;
  capabilities: string[];
  status: string;
  tasks_completed: number;
  tasks_failed: number;
  avg_time_ms: number;
  total_time_ms: number;
  last_event: string | null;
  last_error: string | null;
  running: boolean;
}

interface BusEvent {
  event_id: string;
  event_type: string;
  source: string;
  target: string | null;
  correlation_id: string;
  priority: number;
  timestamp: string;
  payload: Record<string, unknown>;
}

const STATUS_COLORS: Record<string, string> = {
  idle: '#22c55e',
  working: '#3b82f6',
  waiting: '#eab308',
  error: '#ef4444',
  offline: '#6b7280',
};

const AGENT_ICONS: Record<string, string> = {
  coordinator: '🎯',
  research: '🔍',
  validator: '✅',
  exploit: '⚡',
  documentation: '📝',
  strategy: '🧠',
  memory: '💾',
  financial: '💰',
};

function AgentCard({ agent }: { agent: AgentHealth }) {
  const { t } = useI18n();
  const pingColor = STATUS_COLORS[agent.status] || '#6b7280';

  return (
    <div style={{
      background: tokens.colors.surface,
      borderRadius: tokens.radius.lg,
      border: `1px solid ${tokens.colors.border}`,
      padding: tokens.spacing.lg,
      transition: `all ${tokens.animation.normal}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <span style={{ fontSize: 24 }}>{AGENT_ICONS[agent.agent_id] || '🤖'}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: tokens.colors.text }}>
            {agent.name}
          </div>
          <div style={{ fontSize: 12, color: tokens.colors.textMuted, fontFamily: 'monospace' }}>
            {agent.agent_id}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: pingColor,
            boxShadow: `0 0 6px ${pingColor}`,
          }} />
          <span style={{ fontSize: 13, color: pingColor, fontWeight: 500 }}>
            {t[`agent_${agent.status}` as keyof typeof t] || agent.status}
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
        <Metric label={t.agent_tasks_completed} value={String(agent.tasks_completed)} />
        <Metric label={t.agent_tasks_failed} value={String(agent.tasks_failed)} color={agent.tasks_failed > 0 ? '#ef4444' : undefined} />
        <Metric label={t.agent_avg_time} value={`${agent.avg_time_ms.toFixed(0)}ms`} />
        <Metric label={t.agent_total_time} value={`${agent.total_time_ms.toFixed(0)}ms`} />
      </div>

      {agent.last_error && (
        <div style={{ fontSize: 12, color: '#ef4444', padding: '6px 8px', background: 'rgba(239,68,68,0.1)', borderRadius: 6, marginBottom: 8 }}>
          {agent.last_error}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {agent.capabilities.map((cap: string) => (
          <span key={cap} style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 4,
            background: 'rgba(59,130,246,0.1)', color: tokens.colors.accent,
          }}>
            {cap}
          </span>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: tokens.colors.textMuted, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: color || tokens.colors.text }}>{value}</div>
    </div>
  );
}

function EventStream() {
  const { t } = useI18n();
  const [events, setEvents] = useState<BusEvent[]>([]);
  const eventListRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const es = new EventSource(`${API}/events/stream`);
    es.onmessage = (msg) => {
      try {
        const ev = JSON.parse(msg.data);
        setEvents(prev => [ev, ...prev].slice(0, 100));
      } catch { /* ignore parse errors */ }
    };
    es.onerror = () => { /* reconnect automatically */ };
    return () => es.close();
  }, []);

  useEffect(() => {
    if (eventListRef.current) {
      eventListRef.current.scrollTop = 0;
    }
  }, [events]);

  return (
    <div style={{
      background: tokens.colors.surface,
      borderRadius: tokens.radius.lg,
      border: `1px solid ${tokens.colors.border}`,
      padding: tokens.spacing.lg,
      height: '100%',
      display: 'flex', flexDirection: 'column',
    }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: tokens.colors.text, margin: '0 0 12px' }}>
        {t.agent_event_stream}
      </h3>
      <div ref={eventListRef} style={{
        flex: 1, overflowY: 'auto', fontSize: 12, fontFamily: 'monospace',
        display: 'flex', flexDirection: 'column', gap: 4,
      }}>
        {events.length === 0 && (
          <div style={{ color: tokens.colors.textMuted, padding: 16, textAlign: 'center' }}>
            {t.agent_no_events}
          </div>
        )}
        {events.map((ev) => (
          <div key={ev.event_id} style={{
            padding: '4px 8px', borderRadius: 4,
            background: 'rgba(255,255,255,0.03)',
            borderLeft: `2px solid ${STATUS_COLORS[ev.priority <= 3 ? 'working' : 'idle']}`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
              <span style={{ color: tokens.colors.accent }}>{ev.event_type}</span>
              <span style={{ color: tokens.colors.textMuted }}>
                {new Date(ev.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <div style={{ color: tokens.colors.textMuted }}>
              {ev.source} → {ev.target || '*'}
              <span style={{ marginLeft: 8, fontSize: 10 }}>
                corr: {ev.correlation_id.slice(0, 8)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CoordinatorPanel() {
  const { t } = useI18n();
  const [pipelines, setPipelines] = useState<Record<string, unknown>>({});

  useEffect(() => {
    const fetchPipelines = async () => {
      try {
        const res = await fetch(`${API}/coordinator/pipelines`);
        const data = await res.json();
        setPipelines(data.pipelines || {});
      } catch { /* ignore */ }
    };
    fetchPipelines();
    const interval = setInterval(fetchPipelines, 5000);
    return () => clearInterval(interval);
  }, []);

  const pipelineList = Object.entries(pipelines);
  return (
    <div style={{
      background: tokens.colors.surface,
      borderRadius: tokens.radius.lg,
      border: `1px solid ${tokens.colors.border}`,
      padding: tokens.spacing.lg,
    }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: tokens.colors.text, margin: '0 0 12px' }}>
        {t.agent_coordinator_activity}
      </h3>
      {pipelineList.length === 0 && (
        <div style={{ color: tokens.colors.textMuted, fontSize: 13, padding: 8 }}>
          No active pipelines
        </div>
      )}
      {pipelineList.map(([pid, info]) => {
        const i = info as Record<string, unknown>;
        return (
          <div key={pid} style={{
            padding: '8px 12px', borderRadius: 6,
            background: 'rgba(255,255,255,0.03)',
            marginBottom: 8,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontWeight: 600, color: tokens.colors.text }}>
                {String(i.target_name || '?')}
              </span>
              <span style={{
                fontSize: 12, padding: '1px 8px', borderRadius: 4,
                background: String(i.state) === 'completed' ? 'rgba(34,197,94,0.15)' : 'rgba(59,130,246,0.15)',
                color: String(i.state) === 'completed' ? '#22c55e' : '#3b82f6',
              }}>
                {String(i.state || '?')}
              </span>
            </div>
            <div style={{ fontSize: 11, color: tokens.colors.textMuted, fontFamily: 'monospace' }}>
              {pid.slice(0, 12)}... | retries: {String(i.retries || 0)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AgentCenter() {
  const { t } = useI18n();
  const [agents, setAgents] = useState<AgentHealth[]>([]);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API}/health`);
      const data = await res.json();
      const agentList = Object.values(data.agents || {}) as AgentHealth[];
      setAgents(agentList);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 3000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  const onlineCount = agents.filter(a => a.running).length;

  return (
    <div style={{ padding: tokens.spacing.xl, maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: tokens.colors.text, margin: 0 }}>
            {t.agent_center}
          </h1>
          <p style={{ fontSize: 13, color: tokens.colors.textMuted, margin: '4px 0 0' }}>
            {onlineCount}/{agents.length} {t.dashboard_agents_online}
          </p>
        </div>
        <button
          onClick={() => {
            fetch(`${API}/pipeline/start`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ target_id: 0, target_name: 'quick-scan' }),
            }).catch(() => {});
          }}
          style={{
            padding: '8px 20px', borderRadius: 8, border: 'none',
            background: tokens.colors.accent, color: '#fff',
            fontSize: 13, fontWeight: 600, cursor: 'pointer',
            transition: `opacity ${tokens.animation.normal}`,
          }}
        >
          {t.agent_start_pipeline}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16, marginBottom: 24 }}>
        {agents.map((agent) => (
          <AgentCard key={agent.agent_id} agent={agent} />
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <CoordinatorPanel />
        <EventStream />
      </div>
    </div>
  );
}
