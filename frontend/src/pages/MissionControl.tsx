import { useEffect, useMemo, useState, useCallback } from 'react';
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
import { Skeleton, SkeletonCard, SkeletonPanel } from '../components/ui/Skeleton';
import { useUI } from '../lib/store';
import { useIsMobile } from '../lib/useIsMobile';
import { useI18n } from '../lib/i18n';
import type {
  ActivityEvent, TimelineEvent, QuickWin, OpportunityRecommendations,
  MorningBrief,
} from '../types';

const QUICK_ACTIONS = [
  { label: 'Investigations', icon: '◈', path: '/investigations' },
  { label: 'Pipeline', icon: '▤', path: '/pipeline' },
  { label: 'Hypotheses', icon: '⟐', path: '/hypothesis' },
  { label: 'Evidence', icon: '📋', path: '/evidence' },
  { label: 'Reports', icon: '📄', path: '/reports' },
];

function useGreeting() {
  return useCallback(() => {
    const h = new Date().getHours();
    if (h < 12) return 'greeting_morning';
    if (h < 19) return 'greeting_afternoon';
    return 'greeting_evening';
  }, []);
}

function useStatusLine(health: { status: string } | undefined, brief: MorningBrief | null, _evidenceCount: number) {
  return useMemo(() => {
    if (health?.status === 'healthy') {
      return { key: 'status_ok' as const };
    }
    if (brief?.new_targets && brief.new_targets > 0) {
      return { key: 'status_agents_attention' as const, count: 2 };
    }
    return { key: 'status_ok' as const };
  }, [health, brief]);
}

export default function MissionControl() {
  const navigate = useNavigate();
  const { setSelectedTarget } = useUI();
  const isMobile = useIsMobile();
  const { t } = useI18n();
  const getGreetingKey = useGreeting();
  const greetingKey = getGreetingKey();

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

  const statusLine = useStatusLine(health, brief, evidenceRes?.items?.length ?? 0);

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

  useEffect(() => {
    if (missionData?.target?.id) {
      setSelectedTarget(missionData.target.id);
    }
  }, [missionData?.target?.id, setSelectedTarget]);

  const suggestionDefaults = [
    { label: 'Find a better opportunity', icon: '🎯', action: () => navigate('/radar') },
    { label: 'What should I investigate?', icon: '❓', action: () => {} },
    { label: 'Show recent activity', icon: '📋', action: () => navigate('/evidence') },
    { label: 'Open AI Intelligence', icon: '🧠', action: () => navigate('/intelligence') },
  ];

  const suggestions = suggestionDefaults;

  if (overviewLoading) {
    return (
      <div style={{ maxWidth: 1400, animation: 'fadeIn 0.2s ease' }}>
        <div style={{ marginBottom: 24 }}>
          <Skeleton width={200} height={22} />
          <div style={{ marginTop: 8 }}><Skeleton width={280} height={14} /></div>
        </div>
        <div style={{ marginBottom: 20 }}><div style={{ height: 180, background: '#1F252E', borderRadius: 14 }} /></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 12, marginBottom: 24 }}>
          {Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <SkeletonPanel /><SkeletonPanel />
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1400, animation: 'fadeIn 0.2s ease' }}>
      {/* Header — Personalized Welcome */}
      <div style={{
        marginBottom: 24, display: 'flex', justifyContent: 'space-between',
        alignItems: 'flex-end', flexWrap: 'wrap', gap: 8,
      }}>
        <div>
          <h1 style={{
            fontSize: 22, fontWeight: 700, margin: 0, color: '#F8FAFC',
            letterSpacing: '-0.01em',
          }}>
            {t[greetingKey]}.
          </h1>
          <p style={{
            margin: '6px 0 0', fontSize: 13, color: '#A0A8B3',
            fontWeight: 400,
          }}>
            {t[statusLine.key]}
            {'count' in statusLine && ` ${statusLine.count} ${t.status_agents_attention}`}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {health && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 14px', borderRadius: 10,
              background: '#1F252E', border: '1px solid #212838',
            }}>
              <div style={{
                width: 7, height: 7, borderRadius: '50%',
                background: health.status === 'healthy' ? '#22C55E' : '#EF4444',
              }} />
              <span style={{ fontSize: 11, color: '#A0A8B3', fontWeight: 500 }}>
                {health.status === 'healthy' ? 'Healthy' : 'Issues'}
              </span>
            </div>
          )}
          <span style={{ color: '#4A4F63', fontSize: 11, fontWeight: 500 }}>
            {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
          </span>
        </div>
      </div>

      {/* Quick Actions Bar */}
      <div style={{
        display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap',
        padding: '8px 12px', background: '#1F252E', borderRadius: 12,
        border: '1px solid #212838',
      }}>
        {QUICK_ACTIONS.map(a => (
          <button
            key={a.path}
            onClick={() => navigate(a.path)}
            style={{
              padding: '6px 14px', borderRadius: 8, border: '1px solid #212838',
              background: '#161B22', color: '#A0A8B3', fontSize: 11, fontWeight: 500,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#D4AF37'; e.currentTarget.style.background = '#1F252E'; e.currentTarget.style.color = '#F8FAFC'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#212838'; e.currentTarget.style.background = '#161B22'; e.currentTarget.style.color = '#A0A8B3'; }}
          >
            <span>{a.icon}</span>
            <span>{a.label}</span>
          </button>
        ))}
      </div>

      {/* Mission Widget — Primary */}
      <div style={{ marginBottom: 16 }}>
        <MissionWidget data={missionData} loading={!oppRecs} />
      </div>

      {/* KPI Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))',
        gap: 12, marginBottom: 16,
      }}>
        <KPICard label="Active Targets" value={overview?.target_count ?? 0} icon="🎯" accent="rgba(59,130,246,0.12)" />
        <KPICard label="Confirmed" value={overview?.pipeline_stages?.confirmed ?? 0} icon="✅" accent="rgba(34,197,94,0.12)" />
        <KPICard label="High-Signal" value={overview?.high_signal_endpoints ?? 0} icon="📊" accent="rgba(59,130,246,0.12)" />
        <KPICard label="Active Scans" value={overview?.active_scans ?? 0} icon="🔄" accent="rgba(212,175,55,0.12)" />
        <KPICard label="Est. ROI" value={`$${(targets.reduce((s, t) => s + (t.estimated_payout ?? 0), 0)).toLocaleString()}`} icon="💰" accent="rgba(34,197,94,0.12)" />
      </div>

      {/* Reports KPI Row */}
      {reportStats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))',
          gap: 12, marginBottom: 16,
        }}>
          <KPICard label="Reports" value={reportStats.total} icon="📋" accent="rgba(139,92,246,0.12)" />
          <KPICard label="Triaged" value={reportStats.status_counts?.triaged ?? 0} icon="🔍" accent="rgba(34,197,94,0.12)" />
          <KPICard label="Paid" value={reportStats.status_counts?.paid ?? 0} icon="💰" accent="rgba(16,185,129,0.12)" />
          <KPICard label="Total Rewards" value={`$${(reportStats.total_rewards || 0).toLocaleString()}`} icon="🏆" accent="rgba(212,175,55,0.12)" />
          <KPICard label="Est. Rewards" value={`$${(reportStats.estimated_rewards || 0).toLocaleString()}`} icon="📈" accent="rgba(59,130,246,0.12)" />
        </div>
      )}

      {/* Middle Row — Widgets */}
      <div style={{
        display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr',
        gap: 16, marginBottom: 16,
      }}>
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
      <div data-evh-widget style={{ marginBottom: 16 }}>
        <EVHWidget />
      </div>

      {/* Opportunities */}
      <Panel
        title="Today's Opportunities"
        subtitle={oppRecs ? `Top ${oppRecs.top_opportunities.length} public opportunities` : ''}
        accent="#D4AF37"
        loading={!oppRecs}
        empty={!oppRecs?.top_opportunities?.length}
        emptyMessage="Run discovery to find opportunities"
        style={{ marginBottom: 16 }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {(oppRecs?.top_opportunities ?? []).slice(0, 5).map((opp) => (
            <div
              key={opp.id}
              onClick={() => opp.public_url ? window.open(opp.public_url, '_blank') : null}
              style={{
                padding: '10px 12px', borderRadius: 10,
                background: '#1F252E', border: '1px solid #212838',
                fontSize: 12, cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#D4AF37'; e.currentTarget.style.background = '#252C38'; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#212838'; e.currentTarget.style.background = '#1F252E'; }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#F8FAFC', fontWeight: 600 }}>{opp.name}</span>
                <span style={{
                  color: opp.priority === 'high' ? '#22C55E' : opp.priority === 'critical' ? '#EF4444' : '#D4AF37',
                  fontWeight: 700,
                }}>
                  {(opp.score ?? 0).toFixed(2)}
                </span>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 4, color: '#6B7280', fontSize: 10 }}>
                <Badge text={opp.category} variant="stage" />
                <span>{opp.source_name}</span>
                {opp.evh?.value != null && <span>· ${Number(opp.evh.value).toFixed(0)}/hr</span>}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Quick Wins */}
      <Panel
        title="Quick Wins"
        subtitle={`${quickWinsRes?.report?.total_opportunities ?? 0} opportunities · ${quickWinsRes?.report?.total_estimated_value ? `$${quickWinsRes.report.total_estimated_value.toLocaleString()} est. value` : ''}`}
        accent="#22C55E"
        loading={qwLoading}
        empty={!topQuickWins.length}
        emptyMessage="No quick wins identified yet"
        style={{ marginBottom: 16 }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {topQuickWins.map((qw: QuickWin, i: number) => (
            <div key={i} style={{
              padding: '12px 16px', borderRadius: 10,
              background: '#1F252E', border: '1px solid #212838',
              transition: 'all 0.15s ease',
            }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#22C55E'; e.currentTarget.style.background = '#252C38'; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#212838'; e.currentTarget.style.background = '#1F252E'; }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#F8FAFC' }}>{qw.endpoint_method} {qw.endpoint_path}</div>
                  <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{qw.reasoning}</div>
                </div>
                <Badge text={qw.category} variant="severity" color={
                  qw.category === 'ready_to_report' ? '#22C55E' : qw.category === 'half_confirmed' ? '#D4AF37' : qw.category === 'low_hanging_fruit' ? '#3B82F6' : '#6B7280'
                } />
              </div>
              <div style={{ display: 'flex', gap: 20, fontSize: 11, color: '#6B7280' }}>
                <span>Score: <strong style={{ color: '#A0A8B3' }}>{(qw.quick_win_score ?? 0).toFixed(2)}</strong></span>
                <span>Payout: <strong style={{ color: '#22C55E' }}>${(qw.estimated_payout ?? 0).toFixed(0)}</strong></span>
                <span>Effort: <strong style={{ color: '#A0A8B3' }}>{qw.estimated_effort_minutes}min</strong></span>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Technology Distribution */}
      {techDist && techDist.length > 0 && (
        <Panel title="Technology Distribution" subtitle={`${techDist.length} technologies detected across programs`} accent="#D4AF37" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {techDist.slice(0, 25).map((t) => (
              <div
                key={t.technology}
                onClick={() => navigate(`/programs?technology=${t.technology}`)}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 500,
                  background: '#1F252E', border: '1px solid #212838', color: '#A0A8B3',
                  cursor: 'pointer', transition: 'all 0.12s ease',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#D4AF37'; e.currentTarget.style.background = '#252C38'; e.currentTarget.style.color = '#F8FAFC'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#212838'; e.currentTarget.style.background = '#1F252E'; e.currentTarget.style.color = '#A0A8B3'; }}
              >
                <span>{t.technology}</span>
                <span style={{ color: '#6B7280', fontSize: 10 }}>({t.count})</span>
              </div>
            ))}
            <div
              onClick={() => navigate('/programs')}
              style={{
                display: 'inline-flex', alignItems: 'center',
                padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                background: '#D4AF37', color: '#0A0B0F', cursor: 'pointer',
              }}
            >
              View All Programs →
            </div>
          </div>
        </Panel>
      )}

      {/* Bottom Row — Timeline + Evidence + Activity */}
      <div style={{
        display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr',
        gap: 16, marginBottom: 16,
      }}>
        <Panel title="Timeline" subtitle="Recent events" accent="#D4AF37" loading={!timeline} empty={!recentEvents.length} emptyMessage="No timeline events yet">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {recentEvents.map((e: TimelineEvent, i: number) => (
              <div key={i} style={{
                display: 'flex', gap: 10, alignItems: 'flex-start',
                padding: '6px 0', borderBottom: i < recentEvents.length - 1 ? '1px solid #212838' : undefined,
              }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#D4AF37', marginTop: 5, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, color: '#A0A8B3' }}>{e.description}</div>
                  <div style={{ fontSize: 10, color: '#6B7280', marginTop: 2 }}>
                    <Badge text={e.event_type} variant="stage" />
                    {e.timestamp && <span style={{ marginLeft: 6 }}>{new Date(e.timestamp).toLocaleString()}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Recent Evidence" subtitle="Latest records" accent="#3B82F6" loading={!evidenceRes} empty={!evidenceRes?.items?.length} emptyMessage="No evidence collected yet">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(evidenceRes?.items ?? []).slice(0, 6).map((ev) => {
              const method = ev.request_method ?? 'GET';
              const url = ev.request_url ?? '';
              const status = ev.response_status;
              const consistent = ev.consistent ?? false;
              return (
                <div key={ev.id} style={{
                  padding: '10px 12px', borderRadius: 10,
                  background: '#1F252E', border: '1px solid #212838',
                  cursor: 'pointer', transition: 'all 0.15s ease', fontSize: 12,
                }}
                  onClick={() => navigate(`/evidence`)}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#3B82F6'; e.currentTarget.style.background = '#252C38'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#212838'; e.currentTarget.style.background = '#1F252E'; }}
                >
                  <div style={{ color: '#A0A8B3' }}>{method} {url.slice(0, 50)}{url.length > 50 ? '...' : ''}</div>
                  <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#6B7280', marginTop: 4 }}>
                    <span>Status: {status ?? 'N/A'}</span>
                    <Badge text={consistent ? 'Consistent' : 'Inconsistent'} color={consistent ? '#22C55E' : '#EF4444'} />
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel title="Activity Feed" subtitle="Latest system activity" accent="#22C55E" loading={activityLoading} empty={!activity?.events?.length} emptyMessage="No activity yet">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {(activity?.events ?? []).slice(0, 8).map((ev: ActivityEvent, i) => (
              <div key={i} style={{
                display: 'flex', gap: 8, alignItems: 'flex-start',
                padding: '6px 0', borderBottom: i < Math.min(activity?.events?.length ?? 0, 8) - 1 ? '1px solid #212838' : undefined,
              }}>
                <Badge text={ev.type} variant="stage" />
                <div style={{ flex: 1, fontSize: 12, color: '#A0A8B3' }}>
                  {ev.title || ev.status || `${ev.type} #${ev.id}`}
                  <div style={{ fontSize: 10, color: '#6B7280' }}>{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ''}</div>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* View All Reports */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
        <div
          onClick={() => navigate('/reports')}
          style={{
            padding: '8px 16px', borderRadius: 8, cursor: 'pointer',
            background: '#1F252E', border: '1px solid #212838',
            fontSize: 12, color: '#6B7280', fontWeight: 500,
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#D4AF37'; e.currentTarget.style.color = '#F8FAFC'; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#212838'; e.currentTarget.style.color = '#6B7280'; }}
        >
          View All Reports →
        </div>
      </div>
    </div>
  );
}
