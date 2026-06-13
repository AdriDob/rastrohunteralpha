import { useEffect, useState } from 'react';
import { getMorningBrief, getEveningSummary, getUnifiedTimeline, getOperationalMetrics, runSelfTest, getTasks, getFavorites } from '../lib/api';
import type { MorningBrief, EveningSummary, UnifiedTimeline, OperationalMetrics, SelfTestReport, TaskItem, FavoriteItem } from '../types';

export default function OperationsDashboard() {
  const [brief, setBrief] = useState<MorningBrief | null>(null);
  const [summary, setSummary] = useState<EveningSummary | null>(null);
  const [timeline, setTimeline] = useState<UnifiedTimeline | null>(null);
  const [metrics, setMetrics] = useState<OperationalMetrics | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [selfTest, setSelfTest] = useState<SelfTestReport | null>(null);
  const [selfTestLoading, setSelfTestLoading] = useState(false);
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [tab, setTab] = useState<'brief' | 'metrics' | 'timeline' | 'self-test' | 'favorites'>('brief');

  useEffect(() => {
    getMorningBrief().then(setBrief).catch(() => {});
    getEveningSummary().then(setSummary).catch(() => {});
    getUnifiedTimeline(10, 48).then(setTimeline).catch(() => {});
    getOperationalMetrics().then(setMetrics).catch(() => {});
    getTasks().then(r => setTasks(r.items)).catch(() => {});
    getFavorites().then(r => setFavorites(r.items)).catch(() => {});
  }, []);

  const handleSelfTest = async () => {
    setSelfTestLoading(true);
    setSelfTest(null);
    try { setSelfTest(await runSelfTest()); } catch {}
    setSelfTestLoading(false);
  };

  const StatCard = ({ label, value, sub }: { label: string; value: string | number; sub?: string }) => (
    <div style={{ background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8, padding: '14px 16px', flex: 1, minWidth: 140 }}>
      <div style={{ color: '#7c8299', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>{label}</div>
      <div style={{ color: '#fff', fontSize: 22, fontWeight: 800 }}>{value}</div>
      {sub && <div style={{ color: '#4a4f63', fontSize: 11, marginTop: 2 }}>{sub}</div>}
    </div>
  );

  const Tabs = () => (
    <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
      {(['brief', 'metrics', 'timeline', 'favorites', 'self-test'] as const).map(t => (
        <button key={t} onClick={() => setTab(t)}
          style={{
            background: tab === t ? '#7c3aed' : 'transparent', color: tab === t ? '#fff' : '#7c8299',
            border: '1px solid', borderColor: tab === t ? '#7c3aed' : '#2a2e3d',
            borderRadius: 6, padding: '6px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer',
          }}>
          {t === 'brief' ? 'Briefings & Tasks' : t === 'metrics' ? 'Metrics' : t === 'timeline' ? 'Timeline' : t === 'favorites' ? 'My Favorites' : 'System Self Test'}
        </button>
      ))}
    </div>
  );

  return (
    <div>
      <h1 style={{ margin: '0 0 20px', fontSize: 22, fontWeight: 800 }}>Operations Dashboard</h1>

      {/* KPI Row */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 20 }}>
        <StatCard label="Pending Tasks" value={tasks.filter(t => t.status !== 'completed').length} sub={`${tasks.length} total`} />
        <StatCard label="24h Events" value={timeline?.total ?? '—'} sub={timeline ? 'Across all systems' : 'from unified timeline'} />
        {metrics && (
          <>
            <StatCard label="Quick Win Conv." value={`${metrics.quick_win_conversion_rate}%`} sub={`${metrics.confirmed_verdicts}/${metrics.total_verdicts} verdicts`} />
            <StatCard label="Confidence (High)" value={metrics.confidence_distribution.high ?? 0} sub={`medium ${metrics.confidence_distribution.medium ?? 0} · low ${metrics.confidence_distribution.low ?? 0}`} />
          </>
        )}
      </div>

      <Tabs />

      {/* Brief tab */}
      {tab === 'brief' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', gap: 16 }}>
            {brief && (
              <div style={{ flex: 1, background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8, padding: 16 }}>
                <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700, color: '#f59e0b' }}>☀ Morning Brief</h3>
                <p style={{ color: '#7c8299', fontSize: 12, marginBottom: 12 }}>{brief.summary}</p>
                <div style={{ display: 'flex', gap: 10 }}>
                  <StatCard label="New Targets" value={brief.new_targets} />
                  <StatCard label="New Endpoints" value={brief.new_endpoints} />
                  <StatCard label="New Evidence" value={brief.new_evidence} />
                  <StatCard label="Quick Wins" value={brief.quick_wins_count} />
                </div>
                {brief.highest_roi_opportunity && (
                  <div style={{ marginTop: 10, color: '#22c55e', fontSize: 12 }}>
                    Top opportunity: {brief.highest_roi_opportunity.name} (ROI: {brief.highest_roi_opportunity.roi.toFixed(2)})
                  </div>
                )}
              </div>
            )}
            {summary && (
              <div style={{ flex: 1, background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8, padding: 16 }}>
                <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700, color: '#6366f1' }}>🌙 Evening Summary</h3>
                <p style={{ color: '#7c8299', fontSize: 12, marginBottom: 12 }}>{summary.summary}</p>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <StatCard label="Scans" value={summary.scans_executed} />
                  <StatCard label="Endpoints" value={summary.endpoints_discovered} />
                  <StatCard label="Verdicts" value={summary.verdicts_created} />
                  <StatCard label="Findings" value={summary.reports_produced} />
                  <StatCard label="Learning Updates" value={summary.adaptive_learning_updates} />
                </div>
              </div>
            )}
          </div>

          <div style={{ background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8, padding: 16 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700, color: '#e0e0e0' }}>Recent Tasks</h3>
            {tasks.filter(t => t.status !== 'completed').slice(0, 8).map(task => (
              <div key={task.id} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #2a2e3d', fontSize: 13 }}>
                <span style={{ color: task.priority === 'critical' ? '#ef4444' : task.priority === 'high' ? '#f97316' : '#4a4f63' }}>●</span>
                <span style={{ color: '#e0e0e0', flex: 1 }}>{task.title}</span>
                <span style={{ color: '#4a4f63', fontSize: 11 }}>{task.status.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Metrics tab */}
      {tab === 'metrics' && metrics && (
        <div style={{ background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8, padding: 16 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 700 }}>Operational Metrics</h3>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
            <StatCard label="Total Verdicts" value={metrics.total_verdicts} />
            <StatCard label="Confirmed" value={metrics.confirmed_verdicts} />
            <StatCard label="Total Findings" value={metrics.total_findings} />
            <StatCard label="Total Evidence" value={metrics.total_evidence} />
            <StatCard label="Evidence (7d)" value={metrics.evidence_growth_7d} />
            <StatCard label="Findings (7d)" value={metrics.findings_growth_7d} />
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <StatCard label="High Confidence" value={metrics.confidence_distribution.high ?? 0} />
            <StatCard label="Medium Confidence" value={metrics.confidence_distribution.medium ?? 0} />
            <StatCard label="Low Confidence" value={metrics.confidence_distribution.low ?? 0} />
            <StatCard label="Quick Win Conv. Rate" value={`${metrics.quick_win_conversion_rate}%`} />
            <StatCard label="Avg Invest. Time" value={`${metrics.average_investigation_time_minutes}m`} />
            <StatCard label="Avg Report Time" value={`${metrics.average_report_creation_time_minutes}m`} />
          </div>
        </div>
      )}

      {/* Timeline tab */}
      {tab === 'timeline' && (
        <div style={{ background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8, padding: 16 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700 }}>Unified Timeline <span style={{ color: '#4a4f63', fontWeight: 400, fontSize: 12 }}>(last 48h)</span></h3>
          {timeline?.events.map((e, i) => (
            <div key={`${e.type}-${e.id}-${i}`} style={{ display: 'flex', gap: 10, padding: '8px 0', borderBottom: '1px solid #2a2e3d', fontSize: 13, alignItems: 'flex-start' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: e.type === 'finding' ? '#ef4444' : e.type === 'verdict' ? '#f59e0b' : e.type === 'scan' ? '#7c3aed' : e.type === 'evidence' ? '#22c55e' : '#6366f1', marginTop: 4 }} />
              <div style={{ minWidth: 80, color: '#4a4f63', fontSize: 11 }}>{e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : ''}</div>
              <div style={{ minWidth: 70, fontSize: 11, color: '#7c8299' }}>{e.type}</div>
              <div style={{ color: '#e0e0e0', flex: 1 }}>{e.label}</div>
              {'severity' in e && e.severity && <span style={{ color: '#ef4444', fontSize: 11 }}>{e.severity}</span>}
              {'confidence' in e && e.confidence !== undefined && <span style={{ color: '#6366f1', fontSize: 11 }}>{(e.confidence * 100).toFixed(0)}%</span>}
            </div>
          ))}
          {(!timeline || timeline.events.length === 0) && (
            <div style={{ color: '#4a4f63', padding: 20, textAlign: 'center' }}>No events in the last 48h.</div>
          )}
        </div>
      )}

      {/* Favorites tab */}
      {tab === 'favorites' && (
        <div style={{ background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8, padding: 16 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 700 }}>My Favorites</h3>
          {favorites.length === 0 ? (
            <div style={{ color: '#4a4f63', padding: 20, textAlign: 'center' }}>
              No favorites yet. Star targets, endpoints, evidence, or reports from their detail pages.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {favorites.map(f => (
                <div key={f.id} style={{
                  display: 'flex', gap: 10, alignItems: 'center', padding: '8px 12px',
                  background: '#12141f', borderRadius: 6, fontSize: 13,
                }}>
                  <span style={{ color: '#f59e0b' }}>★</span>
                  <span style={{ color: '#7c8299', minWidth: 70, fontSize: 11 }}>{f.item_type}</span>
                  <span style={{ color: '#e0e0e0', flex: 1 }}>{f.label || `${f.item_type} #${f.item_id}`}</span>
                  <span style={{ color: '#4a4f63', fontSize: 11 }}>{new Date(f.created_at).toLocaleDateString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Self Test tab */}
      {tab === 'self-test' && (
        <div style={{ background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8, padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700 }}>System Self Test</h3>
            <button onClick={handleSelfTest} disabled={selfTestLoading}
              style={{ background: selfTestLoading ? '#4a4f63' : '#7c3aed', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 16px', fontSize: 13, fontWeight: 600, cursor: selfTestLoading ? 'wait' : 'pointer' }}>
              {selfTestLoading ? 'Running...' : selfTest ? 'Re-run' : 'Run Self Test'}
            </button>
          </div>
          {selfTest && (
            <>
              <div style={{ marginBottom: 16 }}>
                <span style={{ fontWeight: 700, fontSize: 16, color: selfTest.all_ok ? '#22c55e' : '#ef4444' }}>
                  {selfTest.overall_status === 'healthy' ? '✓ All Systems Healthy' : '✗ Degraded'}
                </span>
                <span style={{ color: '#4a4f63', fontSize: 13, marginLeft: 12 }}>{selfTest.summary}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {selfTest.components.map(c => (
                  <div key={c.component} style={{
                    display: 'flex', gap: 10, alignItems: 'center', padding: '8px 12px',
                    background: c.status === 'ok' ? '#12141f' : '#1f1212', borderRadius: 6, fontSize: 13,
                  }}>
                    <span style={{ color: c.status === 'ok' ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                      {c.status === 'ok' ? '✓' : '✗'}
                    </span>
                    <span style={{ color: '#e0e0e0', minWidth: 150 }}>{c.component}</span>
                    <span style={{ color: c.status === 'ok' ? '#22c55e' : '#ef4444', fontSize: 12 }}>{c.detail}</span>
                  </div>
                ))}
              </div>
            </>
          )}
          {!selfTest && !selfTestLoading && (
            <div style={{ color: '#4a4f63', padding: 20, textAlign: 'center' }}>Click "Run Self Test" to verify all system components are operational.</div>
          )}
        </div>
      )}
    </div>
  );
}
