import {
  useExecutionTrackerStats,
  useExecutionScorecard,
  useExecutionExplanations,
  useExecutionTraces,
  useExecutionDecisions,
  useExecutionInsights,
  useExecutionOutcomes,
} from '../lib/query';
import Panel from './ui/Panel';
import Badge from './ui/Badge';
import { SkeletonPanel } from './ui/Skeleton';

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: '12px 16px' }}>
      <div style={{ fontSize: 10, color: '#7c8299', fontWeight: 600, textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color, marginTop: 4 }}>{value}</div>
    </div>
  );
}

export function ExecutionScorecard() {
  const { data, isLoading } = useExecutionScorecard();

  if (isLoading) return <SkeletonPanel />;
  if (!data) return null;

  const { latest, trend } = data;

  return (
    <Panel title="System Scorecard">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8, marginBottom: 12 }}>
        <StatCard label="Actions" value={latest.total_actions} color="#3b82f6" />
        <StatCard label="Success Rate" value={`${(latest.success_rate * 100).toFixed(0)}%`} color="#22c55e" />
        <StatCard label="Avg Score" value={latest.avg_outcome_score.toFixed(2)} color="#a855f7" />
        <StatCard label="Memory" value={latest.memory_usage} color="#eab308" />
      </div>
      <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#7c8299' }}>
        <span>Health: <Badge variant={latest.system_health === 'healthy' ? 'success' : 'warning'}>{latest.system_health}</Badge></span>
        <span>Trend: <span style={{ color: trend.trend === 'improving' ? '#22c55e' : trend.trend === 'declining' ? '#ef4444' : '#7c8299' }}>{trend.trend}</span></span>
        <span>Delta: {(trend.delta * 100).toFixed(1)}%</span>
      </div>
    </Panel>
  );
}

export function ExecutionRecent() {
  const { data: stats, isLoading } = useExecutionTrackerStats();

  if (isLoading) return <SkeletonPanel />;
  if (!stats) return null;

  const recent = stats.recent || [];

  return (
    <Panel title="Recent Executions">
      {recent.length === 0 ? (
        <div style={{ fontSize: 12, color: '#7c8299' }}>No recent executions</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {recent.slice(0, 10).map((exec) => (
            <div key={`${exec.action_id}-${exec.timestamp}`} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '6px 10px', borderRadius: 6, background: '#1a1e2b', fontSize: 12,
            }}>
              <div>
                <span style={{ color: '#e2e8f0' }}>{exec.label}</span>
                <span style={{ color: '#7c8299', marginLeft: 8 }}>{exec.action_type}</span>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ color: exec.status === 'error' ? '#ef4444' : '#22c55e' }}>{exec.status}</span>
                <span style={{ color: '#7c8299' }}>{exec.duration_ms.toFixed(0)}ms</span>
                <Badge variant={exec.outcome_score > 0.7 ? 'success' : exec.outcome_score > 0.3 ? 'warning' : 'error'}>
                  {exec.outcome_score.toFixed(2)}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

export function ExecutionExplanations() {
  const { data, isLoading } = useExecutionExplanations(10);

  if (isLoading) return <SkeletonPanel />;
  if (!data) return null;

  const { explanations, count } = data;

  return (
    <Panel title={`Explanations (${count})`}>
      {explanations.length === 0 ? (
        <div style={{ fontSize: 12, color: '#7c8299' }}>No explanations yet</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {explanations.map((exp) => (
            <div key={exp.id} style={{
              padding: '8px 12px', borderRadius: 6, background: '#1a1e2b', fontSize: 12,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{exp.action}</span>
                <Badge variant={exp.confidence > 0.7 ? 'success' : 'warning'}>
                  {exp.confidence.toFixed(2)}
                </Badge>
              </div>
              <div style={{ color: '#7c8299' }}>{exp.summary}</div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

export function ExecutionTraces() {
  const { data, isLoading } = useExecutionTraces(10);

  if (isLoading) return <SkeletonPanel />;
  if (!data) return null;

  const { traces, count } = data;

  return (
    <Panel title={`Decision Traces (${count})`}>
      {traces.length === 0 ? (
        <div style={{ fontSize: 12, color: '#7c8299' }}>No traces yet</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {traces.map((trace) => (
            <div key={trace.trace_id} style={{
              padding: '8px 12px', borderRadius: 6, background: '#1a1e2b', fontSize: 12,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{trace.action}</span>
                <span style={{ color: '#7c8299' }}>{trace.steps.length} steps · {trace.total_duration_ms.toFixed(0)}ms</span>
              </div>
              {trace.steps.length > 0 && (
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {trace.steps.map((step, i) => (
                    <Badge key={i} variant="default">{step.name}</Badge>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

export function ExecutionDecisions() {
  const { data, isLoading } = useExecutionDecisions(10);

  if (isLoading) return <SkeletonPanel />;
  if (!data) return null;

  const { decisions, count } = data;

  return (
    <Panel title={`Decision Memory (${count})`}>
      {decisions.length === 0 ? (
        <div style={{ fontSize: 12, color: '#7c8299' }}>No decisions recorded</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {decisions.map((d) => {
            const det = d.details;
            return (
              <div key={d.id} style={{
                padding: '8px 12px', borderRadius: 6, background: '#1a1e2b', fontSize: 12,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{det?.action || d.key}</span>
                  <Badge variant={det?.outcome === 'success' ? 'success' : det?.outcome === 'error' ? 'error' : 'default'}>
                    {det?.outcome || 'pending'}
                  </Badge>
                </div>
                {det?.reason && <div style={{ color: '#7c8299' }}>{det.reason}</div>}
                <div style={{ color: '#4b5563', marginTop: 2 }}>
                  confidence: {det?.confidence?.toFixed(2)} · {det?.source}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}

export function ExecutionInsights() {
  const { data, isLoading } = useExecutionInsights(10);

  if (isLoading) return <SkeletonPanel />;
  if (!data) return null;

  const { insights, count, by_type } = data;

  return (
    <Panel title={`Insight Archive (${count})`}>
      {Object.keys(by_type).length > 0 && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
          {Object.entries(by_type).map(([type, cnt]) => (
            <Badge key={type} variant="default">{type}: {cnt}</Badge>
          ))}
        </div>
      )}
      {insights.length === 0 ? (
        <div style={{ fontSize: 12, color: '#7c8299' }}>No insights archived</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {insights.map((ins) => {
            const det = ins.details;
            return (
              <div key={ins.id} style={{
                padding: '8px 12px', borderRadius: 6, background: '#1a1e2b', fontSize: 12,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{det?.title || ins.key}</span>
                  <Badge variant={det?.severity === 'critical' ? 'error' : det?.severity === 'high' ? 'warning' : 'default'}>
                    {det?.severity || 'info'}
                  </Badge>
                </div>
                {det?.description && <div style={{ color: '#7c8299' }}>{det.description}</div>}
                <div style={{ color: '#4b5563', marginTop: 2 }}>
                  {det?.insight_type} · {det?.source} · {det?.tags?.join(', ')}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}

export function ExecutionOutcomes() {
  const { data, isLoading } = useExecutionOutcomes(10);

  if (isLoading) return <SkeletonPanel />;
  if (!data) return null;

  const { summary } = data;

  return (
    <Panel title="Outcome Summary">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8 }}>
        <StatCard label="Total" value={summary.total} color="#3b82f6" />
        <StatCard label="Success Rate" value={`${(summary.success_rate * 100).toFixed(0)}%`} color="#22c55e" />
        {Object.entries(summary.by_type).slice(0, 4).map(([type, stats]) => (
          <StatCard key={type} label={type} value={`${(stats.success_rate * 100).toFixed(0)}%`} color="#a855f7" />
        ))}
      </div>
    </Panel>
  );
}

export default function ExecutionPanel() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <ExecutionScorecard />
      <ExecutionOutcomes />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <ExecutionRecent />
        <ExecutionExplanations />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <ExecutionTraces />
        <ExecutionDecisions />
      </div>
      <ExecutionInsights />
    </div>
  );
}
