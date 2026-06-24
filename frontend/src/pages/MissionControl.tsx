import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  useOverview, useQuickWins, useActivity,
  useTargets, useEvidence, useTimeline, useSystemHealth,
  useReportStats, useTechnologyDistribution,
} from '../lib/query';
import { getOpportunityRecommendations, getMorningBrief } from '../lib/api';
import KPICard from '../components/layout/KPICard';
import Panel from '../components/ui/Panel';
import Badge from '../components/ui/Badge';
import MissionWidget from '../components/MissionWidget';
import EVHWidget from '../components/EVHWidget';
import IdentityVaultWidget from '../components/IdentityVaultWidget';
import ProviderHealthWidget from '../components/ProviderHealthWidget';
import AssistantPanel from '../components/AssistantPanel';
import { SkeletonCard, SkeletonPanel } from '../components/ui/Skeleton';
import { useStore, useUI } from '../lib/store';
import { useIsMobile } from '../lib/useIsMobile';
import type {
  ActivityEvent, TimelineEvent, QuickWin, OpportunityRecommendations,
  MorningBrief, Target,
} from '../types';

const QUICK_ACTIONS = [
  { label: 'Investigations', icon: '◈', path: '/investigations' },
  { label: 'Pipeline', icon: '▤', path: '/pipeline' },
  { label: 'Hypotheses', icon: '⟐', path: '/hypothesis' },
  { label: 'Evidence', icon: '📋', path: '/evidence' },
  { label: 'Reports', icon: '📄', path: '/reports' },
];

const suggestionMap: Record<string, { label: string; icon: string; action: () => void }[]> = {
  '/': [
    { label: 'Find a better opportunity', icon: '🎯', action: () => window.location.href = '/radar' },
    { label: 'Show EVH rankings', icon: '💰', action: () => document.querySelector('[data-evh-widget]')?.scrollIntoView({ behavior: 'smooth' }) },
    { label: 'What changed?', icon: '🔄', action: () => window.location.href = '/differential' },
    { label: 'Generate report', icon: '📄', action: () => window.location.href = '/reports' },
  ],
};

const suggestionDefaults = [
  { label: 'Find a better opportunity', icon: '🎯', action: () => window.location.href = '/radar' },
  { label: 'What should I investigate?', icon: '❓', action: () => {} },
  { label: 'Show recent activity', icon: '📋', action: () => window.location.href = '/evidence' },
  { label: 'Open AI Intelligence', icon: '🧠', action: () => window.location.href = '/intelligence' },
];

export default function MissionControl() {
  const navigate = useNavigate();
  const { setSelectedTarget, incrementAssistantInvocations } = useUI();
  const isMobile = useIsMobile();

  const { data: overview, isLoading: overviewLoading } = useOverview();
  const { data: targetsRes } = useTargets({ limit: 100 });
  const { data: quickWinsRes, isLoading: qwLoading } = useQuickWins();
  const { data: activity, isLoading: activityLoading } = useActivity(10);
  const { data: timeline } = useTimeline(undefined, 10);
  const { data: evidenceRes } = useEvidence(null, { limit: 5 });
  const { data: health } = useSystemHealth();
  const { data: reportStats } = useReportStats();
  const { data: techDist } = useTechnologyDistribution();

  const [oppRecs, setOppRecs] = useState<OpportunityRecommendations | null>(null);
  const [brief, setBrief] = useState<MorningBrief | null>(null);

  useEffect(() => {
    getOpportunityRecommendations().then(setOppRecs).catch(() => {});
    getMorningBrief().then(setBrief).catch(() => {});
  }, []);

  const targets = targetsRes?.items ?? [];

  const topQuickWins = useMemo(() => {
    if (!quickWinsRes?.report?.top_quick_wins) return [];
    return quickWinsRes.report.top_quick_wins.slice(0, 5);
  }, [quickWinsRes]);

  const recentEvents = useMemo(() => {
    if (!timeline?.events) return [];
    return timeline.events.slice(0, 6);
  }, [timeline]);

  const suggestions = suggestionMap[window.location.pathname] || suggestionDefaults;

  const missionData = useMemo(() => {
    const allRecs = oppRecs?.top_opportunities || [];
    if (allRecs.length === 0) return null;
    const top = allRecs[0];
    const topName = (top.name ?? '').toLowerCase();
    const bestTarget = targets.find(t => (t.name ?? '').toLowerCase().includes(topName)) || targets[0];
    return {
      target: bestTarget,
      opportunity: top,
      score: top.score ?? 0,
      priority: top.priority ?? 'medium',
      estimatedRoi: top.estimated_payout || bestTarget?.estimated_payout || 0,
      estimatedEffort: top.estimated_effort_hours ? `~${top.estimated_effort_hours}h` : '~2-4 hours',
      confidence: top.confidence ?? 0,
      reasoning: (top.reasoning ?? []).length > 0 ? top.reasoning : ['Top-scored public opportunity', `${top.source_name ?? 'unknown'} platform`, `${top.category ?? 'general'} category`],
      recommendedAction: top.public_url ? 'Open Opportunity →' : 'Start Investigation →',
      scoreBreakdown: top.score_breakdown,
      evh: top.evh,
    };
  }, [oppRecs, targets]);

  // Auto-select the mission target for system context
  useEffect(() => {
    if (missionData?.target?.id) {
      setSelectedTarget(missionData.target.id);
    }
  }, [missionData?.target?.id, setSelectedTarget]);

  if (overviewLoading) {
    return (
      <div style={{ maxWidth: 1400 }}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#fff' }}>Mission Control</div>
          <div style={{ fontSize: 13, color: '#7c8299' }}>Loading your workspace...</div>
        </div>
        <div style={{ marginBottom: 20 }}><div style={{ height: 180, background: '#1e2230', borderRadius: 12 }} /></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
          {Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <SkeletonPanel /><SkeletonPanel />
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1400 }}>
      {/* Header */}
      <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Mission Control</h1>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>
            {brief?.summary || 'What matters most, right now.'}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {health && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 8, background: '#1e2230', border: '1px solid #2a2e3d' }}>
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: health.status === 'healthy' ? '#22c55e' : '#ef4444' }} />
              <span style={{ fontSize: 11, color: '#7c8299' }}>{health.status === 'healthy' ? 'Healthy' : 'Issues'}</span>
            </div>
          )}
          <span style={{ color: '#4a4f63', fontSize: 11 }}>
            {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
          </span>
        </div>
      </div>

      {/* Quick Actions Bar */}
      <div style={{
        display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap',
        padding: '8px 12px', background: '#1e2230', borderRadius: 8,
        border: '1px solid #2a2e3d',
      }}>
        {QUICK_ACTIONS.map(a => (
          <button
            key={a.path}
            onClick={() => navigate(a.path)}
            style={{
              padding: '6px 14px', borderRadius: 6, border: '1px solid #2a2e3d',
              background: '#12141f', color: '#c4c7d0', fontSize: 11, fontWeight: 600,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
              transition: 'all 0.12s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#7c3aed'; e.currentTarget.style.background = '#1e2230'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2e3d'; e.currentTarget.style.background = '#12141f'; }}
          >
            <span>{a.icon}</span>
            <span>{a.label}</span>
          </button>
        ))}
      </div>

      {/* MISSION FIRST — dominant widget */}
      <MissionWidget data={missionData} loading={!oppRecs} />

      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 10, margin: '20 0' }}>
        <KPICard label="Active Targets" value={overview?.target_count ?? 0} icon="🎯" accent="rgba(124,58,237,0.12)" />
        <KPICard label="Confirmed" value={overview?.pipeline_stages?.confirmed ?? 0} icon="✅" accent="rgba(34,197,94,0.12)" />
        <KPICard label="High-Signal" value={overview?.high_signal_endpoints ?? 0} icon="📊" accent="rgba(59,130,246,0.12)" />
        <KPICard label="Active Scans" value={overview?.active_scans ?? 0} icon="🔄" accent="rgba(234,179,8,0.12)" />
        <KPICard label="Est. ROI" value={`$${(targets.reduce((s: number, t: Target) => s + (t.estimated_payout ?? 0), 0)).toLocaleString()}`} icon="💰" accent="rgba(34,197,94,0.12)" />
      </div>

      {/* Reports KPI row */}
      {reportStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 10, margin: '0 0 20 0' }}>
          <KPICard label="Reports" value={reportStats.total} icon="📋" accent="rgba(139,92,246,0.12)" />
          <KPICard label="Triaged" value={reportStats.status_counts?.triaged ?? 0} icon="🔍" accent="rgba(34,197,94,0.12)" />
          <KPICard label="Paid" value={reportStats.status_counts?.paid ?? 0} icon="💰" accent="rgba(16,185,129,0.12)" />
          <KPICard label="Total Rewards" value={`$${(reportStats.total_rewards || 0).toLocaleString()}`} icon="🏆" accent="rgba(250,204,21,0.12)" />
          <KPICard label="Est. Rewards" value={`$${(reportStats.estimated_rewards || 0).toLocaleString()}`} icon="📈" accent="rgba(59,130,246,0.12)" />
        </div>
      )}

      {/* MIDDLE ROW: 3-column widget grid */}
      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr', gap: 16, marginBottom: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <AssistantPanel
            suggestions={suggestions}
            context={brief ? `${brief.new_targets} new targets · ${brief.new_endpoints} new endpoints in 24h` : ''}
          />
        </div>
        <ProviderHealthWidget />
        <IdentityVaultWidget />
      </div>

      {/* EVH Rankings */}
      <div data-evh-widget>
        <EVHWidget />
      </div>

      {/* Top Opportunities */}
      <Panel
        title="Today's Opportunities"
        subtitle={oppRecs ? `Top ${oppRecs.top_opportunities.length} public opportunities` : ''}
        accent="#6366f1"
        loading={!oppRecs}
        empty={!oppRecs?.top_opportunities?.length}
        emptyMessage="Run discovery to find opportunities"
        style={{ marginTop: 16 }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {(oppRecs?.top_opportunities ?? []).slice(0, 5).map((opp) => (
            <div
              key={opp.id}
              onClick={() => opp.public_url ? window.open(opp.public_url, '_blank') : null}
              style={{
                padding: '8px 10px', borderRadius: 6,
                background: '#1e2230', border: '1px solid #2a2e3d',
                fontSize: 12, cursor: 'pointer', transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#6366f1'; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2a2e3d'; }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#e2e4e9', fontWeight: 600 }}>{opp.name}</span>
                <span style={{ color: opp.priority === 'high' ? '#22c55e' : opp.priority === 'critical' ? '#ef4444' : '#f59e0b', fontWeight: 700 }}>
                  {(opp.score ?? 0).toFixed(2)}
                </span>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 4, color: '#7c8299', fontSize: 10 }}>
                <Badge text={opp.category} variant="stage" />
                <span>{opp.source_name}</span>
                {opp.evh?.value != null && <span>· $${Number(opp.evh.value).toFixed(0)}/hr</span>}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Quick Wins */}
      <Panel
        title="Quick Wins"
        subtitle={`${quickWinsRes?.report?.total_opportunities ?? 0} opportunities · ${quickWinsRes?.report?.total_estimated_value ? `$${quickWinsRes.report.total_estimated_value.toLocaleString()} est. value` : ''}`}
        accent="#22c55e"
        loading={qwLoading}
        empty={!topQuickWins.length}
        emptyMessage="No quick wins identified yet"
        style={{ marginBottom: 16 }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {topQuickWins.map((qw: QuickWin, i: number) => (
            <div key={i} style={{
              padding: '12px 14px', borderRadius: 8, background: '#1e2230', border: '1px solid #2a2e3d', transition: 'all 0.15s',
            }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#22c55e'; e.currentTarget.style.background = '#222639'; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2a2e3d'; e.currentTarget.style.background = '#1e2230'; }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e4e9' }}>{qw.endpoint_method} {qw.endpoint_path}</div>
                  <div style={{ fontSize: 11, color: '#7c8299', marginTop: 2 }}>{qw.reasoning}</div>
                </div>
                <Badge text={qw.category} variant="severity" color={
                  qw.category === 'ready_to_report' ? '#22c55e' : qw.category === 'half_confirmed' ? '#eab308' : qw.category === 'low_hanging_fruit' ? '#3b82f6' : '#6b7280'
                } />
              </div>
              <div style={{ display: 'flex', gap: 20, fontSize: 11, color: '#7c8299' }}>
                <span>Score: <strong style={{ color: '#e2e4e9' }}>{(qw.quick_win_score ?? 0).toFixed(2)}</strong></span>
                <span>Payout: <strong style={{ color: '#22c55e' }}>${(qw.estimated_payout ?? 0).toFixed(0)}</strong></span>
                <span>Effort: <strong style={{ color: '#e2e4e9' }}>{qw.estimated_effort_minutes}min</strong></span>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Technology Distribution */}
      {techDist && techDist.length > 0 && (
        <Panel title="Technology Distribution" subtitle={`${techDist.length} technologies detected across programs`} accent="#a855f7" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {techDist.slice(0, 25).map((t) => (
              <div
                key={t.technology}
                onClick={() => navigate(`/programs?technology=${t.technology}`)}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                  background: '#1e2230', border: '1px solid #2a2e3d', color: '#c4c7d0',
                  cursor: 'pointer', transition: 'all 0.12s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#a855f7'; e.currentTarget.style.background = '#252836'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2a2e3d'; e.currentTarget.style.background = '#1e2230'; }}
              >
                <span>{t.technology}</span>
                <span style={{ color: '#7c8299', fontSize: 10 }}>({t.count})</span>
              </div>
            ))}
            <div
              onClick={() => navigate('/programs')}
              style={{
                display: 'inline-flex', alignItems: 'center',
                padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                background: '#7c3aed', color: '#fff', cursor: 'pointer',
              }}
            >
              View All Programs →
            </div>
          </div>
        </Panel>
      )}

      {/* BOTTOM: Timeline + Evidence + Activity */}
      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr', gap: 16, marginBottom: 16 }}>
        <Panel title="Timeline" subtitle="Recent events" accent="#8b5cf6" loading={!timeline} empty={!recentEvents.length} emptyMessage="No timeline events">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {recentEvents.map((e: TimelineEvent, i: number) => (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '5px 0', borderBottom: i < recentEvents.length - 1 ? '1px solid #2a2e3d' : undefined }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#7c3aed', marginTop: 4, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, color: '#c4c7d0' }}>{e.description}</div>
                  <div style={{ fontSize: 10, color: '#7c8299', marginTop: 2 }}>
                    <Badge text={e.event_type} variant="stage" />
                    {e.timestamp && <span style={{ marginLeft: 6 }}>{new Date(e.timestamp).toLocaleString()}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Recent Evidence" subtitle="Latest records" accent="#f97316" loading={!evidenceRes} empty={!evidenceRes?.items?.length} emptyMessage="No evidence collected">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(evidenceRes?.items ?? []).slice(0, 6).map((ev: import('../types').Evidence) => {
              const method = ev.request_method ?? 'GET';
              const url = ev.request_url ?? '';
              const status = ev.response_status;
              const consistent = ev.consistent ?? false;
              return (
                <div key={ev.id} style={{
                  padding: '8px 10px', borderRadius: 6, background: '#1e2230', border: '1px solid #2a2e3d', cursor: 'pointer', transition: 'all 0.15s', fontSize: 12,
                }}
                  onClick={() => navigate(`/evidence`)}
                >
                  <div style={{ color: '#c4c7d0' }}>{method} {url.slice(0, 50)}{url.length > 50 ? '...' : ''}</div>
                  <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#7c8299', marginTop: 4 }}>
                    <span>Status: {status ?? 'N/A'}</span>
                    <Badge text={consistent ? 'Consistent' : 'Inconsistent'} color={consistent ? '#22c55e' : '#ef4444'} />
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel title="Activity Feed" subtitle="Latest system activity" accent="#3b82f6" loading={activityLoading} empty={!activity?.events?.length} emptyMessage="No activity">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {(activity?.events ?? []).slice(0, 8).map((ev: ActivityEvent, i: number) => (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '5px 0', borderBottom: i < Math.min(activity?.events?.length ?? 0, 8) - 1 ? '1px solid #2a2e3d' : undefined }}>
                <Badge text={ev.type} variant="stage" />
                <div style={{ flex: 1, fontSize: 12, color: '#c4c7d0' }}>
                  {ev.title || ev.status || `${ev.type} #${ev.id}`}
                  <div style={{ fontSize: 10, color: '#7c8299' }}>{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ''}</div>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
        <div
          onClick={() => navigate('/reports')}
          style={{
            padding: '8px 16px', borderRadius: 6, cursor: 'pointer',
            background: '#1e2230', border: '1px solid #2a2e3d', fontSize: 12, color: '#7c8299',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#7c3aed'; e.currentTarget.style.color = '#fff'; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2a2e3d'; e.currentTarget.style.color = '#7c8299'; }}
        >
          View All Reports →
        </div>
      </div>

      <button
        onClick={() => { useStore.getState().setAssistantOpen(true); incrementAssistantInvocations(); }}
        style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 100,
          width: 44, height: 44, borderRadius: '50%', border: 'none', cursor: 'pointer',
          background: '#7c3aed', color: '#fff', fontSize: 20, boxShadow: '0 4px 16px rgba(124,58,237,0.4)',
          display: 'none', alignItems: 'center', justifyContent: 'center',
        }}
      >
        🧠
      </button>
    </div>
  );
}
