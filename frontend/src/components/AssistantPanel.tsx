import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../lib/store';
import {
  getAssistantSummary, getAssistantInsights,
  getAssistantRecommendations, getAssistantNextAction,
  getAssistantDailyBriefing, getBountyPotential,
} from '../lib/api';
import { useSystemState } from '../lib/api/system';
import type { AssistantSummary, AssistantInsight, AssistantRecommendation, AssistantNextAction, DailyBriefing, BountyPotential } from '../types';

export interface Suggestion {
  label: string;
  icon: string;
  action: () => void;
}

interface Props {
  title?: string;
  suggestions?: Suggestion[];
  context?: string;
  compact?: boolean;
  currentPath?: string;
}

function getContextSuggestions(path?: string): Suggestion[] {
  if (!path) return DEFAULT_SUGGESTIONS;
  if (path === '/' || path === '') {
    return [
      { label: 'Open Daily Briefing', icon: '🌅', action: () => window.location.href = '/daily' },
      { label: 'Check Hot Paths', icon: '⚡', action: () => window.location.href = '/hotpaths' },
      { label: 'Review Open Tasks', icon: '✓', action: () => window.location.href = '/tasks' },
      { label: 'Explore Opportunities', icon: '🎯', action: () => window.location.href = '/radar' },
    ];
  }
  if (path.startsWith('/target/')) {
    return [
      { label: 'View Attack Surface', icon: '◉', action: () => window.location.href = '/surface' },
      { label: 'Explain Investigation', icon: '🔬', action: () => window.location.href = '/insights' },
      { label: 'Estimate Bounty', icon: '💰', action: () => window.location.href = '/intelligence' },
      { label: 'Generate Report', icon: '📄', action: () => window.location.href = '/reports' },
    ];
  }
  if (path.startsWith('/evidence') || path.startsWith('/screenshots')) {
    return [
      { label: 'View Pipeline Status', icon: '▤', action: () => window.location.href = '/pipeline' },
      { label: 'Review Hypothesis Queue', icon: '⟐', action: () => window.location.href = '/hypothesis' },
      { label: 'Check Confidence', icon: '📊', action: () => window.location.href = '/confidence' },
    ];
  }
  if (path.startsWith('/insights') || path.startsWith('/hypothesis') || path.startsWith('/differential')) {
    return [
      { label: 'View Attack Surface', icon: '◉', action: () => window.location.href = '/surface' },
      { label: 'Run Discovery Engine', icon: '🔍', action: () => window.location.href = '/pipeline' },
      { label: 'Review Evidence', icon: '📋', action: () => window.location.href = '/evidence' },
    ];
  }
  if (path.startsWith('/operations') || path.startsWith('/tasks') || path.startsWith('/actions')) {
    return [
      { label: 'View History', icon: '☰', action: () => window.location.href = '/history' },
      { label: 'Mission Control', icon: '◈', action: () => window.location.href = '/' },
      { label: 'Check AI Intelligence', icon: '🧠', action: () => window.location.href = '/intelligence' },
    ];
  }
  if (path.startsWith('/intelligence') || path.startsWith('/radar') || path.startsWith('/reports')) {
    return [
      { label: 'Open Top Opportunity', icon: '🏆', action: () => window.location.href = '/radar' },
      { label: 'View Mission Dashboard', icon: '◈', action: () => window.location.href = '/' },
      { label: 'Generate Report', icon: '📄', action: () => window.location.href = '/reports' },
    ];
  }
  return DEFAULT_SUGGESTIONS;
}

const DEFAULT_SUGGESTIONS: Suggestion[] = [
  { label: 'Show top opportunities', icon: '🎯', action: () => window.location.href = '/radar' },
  { label: 'What should I investigate?', icon: '❓', action: () => window.location.href = '/' },
  { label: 'Open AI Intelligence', icon: '🧠', action: () => window.location.href = '/intelligence' },
  { label: 'Review recent evidence', icon: '📋', action: () => window.location.href = '/evidence' },
];

export default function AssistantPanel({ title = 'AI Assistant', suggestions, context, compact, currentPath }: Props) {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<AssistantSummary | null>(null);
  const [insights, setInsights] = useState<AssistantInsight[]>([]);
  const [recommendations, setRecommendations] = useState<AssistantRecommendation[]>([]);
  const [nextAction, setNextAction] = useState<AssistantNextAction | null>(null);
  const [briefing, setBriefing] = useState<DailyBriefing | null>(null);
  const [bounty, setBounty] = useState<BountyPotential | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(!compact);
  const { assistantOpen, setAssistantOpen } = useStore();

  const { data: sysState } = useSystemState();
  const isDegraded = sysState?.state?.system_state === 'DEGRADED' || sysState?.state?.system_state === 'FAILED';
  const topTarget = summary?.top_target ?? null;

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getAssistantSummary().then(setSummary).catch(() => {}),
      getAssistantInsights().then(r => setInsights((r.insights ?? []).slice(0, 3))).catch(() => {}),
      getAssistantRecommendations().then(r => setRecommendations((r.recommendations ?? []).slice(0, 3))).catch(() => {}),
      getAssistantNextAction().then(setNextAction).catch(() => {}),
      getAssistantDailyBriefing().then(setBriefing).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (topTarget?.id) {
      getBountyPotential(topTarget.id).then(setBounty).catch(() => {});
    }
  }, [topTarget?.id]);

  if (compact && !assistantOpen) return null;

  const chips = suggestions || getContextSuggestions(currentPath);

  return (
    <div style={{
      background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 10,
      overflow: 'hidden', transition: 'all 0.2s',
    }}>
      <div
        onClick={() => compact ? setAssistantOpen(!assistantOpen) : setExpanded(!expanded)}
        style={{
          padding: '10px 14px', borderBottom: '1px solid #2a2e3d',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>🧠</span>
          <span style={{ fontWeight: 700, fontSize: 13, color: '#e0e0e0' }}>{title}</span>
        </div>
        <span style={{ color: '#4a4f63', fontSize: 12 }}>{compact ? (assistantOpen ? '−' : '+') : (expanded ? '−' : '+')}</span>
      </div>

      {expanded && (
        <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {loading && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ height: 10, width: '80%', background: '#252836', borderRadius: 3 }} />
              <div style={{ height: 10, width: '60%', background: '#252836', borderRadius: 3 }} />
              <div style={{ height: 10, width: '70%', background: '#252836', borderRadius: 3 }} />
            </div>
          )}

          {isDegraded && (
            <div style={{
              padding: '10px 12px', borderRadius: 8,
              background: 'linear-gradient(135deg, rgba(245,158,11,0.15) 0%, rgba(251,191,36,0.1) 100%)',
              border: '1px solid rgba(245,158,11,0.3)',
            }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#f59e0b', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>⚠️ System Degraded</div>
              <div style={{ fontSize: 12, color: '#e0e0e0' }}>Some services are unhealthy</div>
              <div style={{ fontSize: 11, color: '#c4c7d0', marginTop: 2 }}>
                <span style={{ color: '#60a5fa', cursor: 'pointer', textDecoration: 'underline' }} onClick={() => navigate('/')}>View Status</span> for details.
              </div>
            </div>
          )}

          {!loading && nextAction && (
            <div style={{
              padding: '10px 12px', borderRadius: 8,
              background: 'linear-gradient(135deg, rgba(124,58,237,0.15) 0%, rgba(99,102,241,0.1) 100%)',
              border: '1px solid rgba(124,58,237,0.3)',
              cursor: nextAction.route ? 'pointer' : 'default',
            }}
              onClick={() => nextAction.route ? navigate(nextAction.route) : nextAction.url ? window.open(nextAction.url, '_blank') : {}}
            >
              <div style={{ fontSize: 10, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>🎯 Next Best Action</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>{nextAction.recommended_action}</div>
              <div style={{ fontSize: 11, color: '#c4c7d0', marginTop: 2 }}>{nextAction.reasoning}</div>
            </div>
          )}

          {!loading && summary && (
            <div style={{ fontSize: 12, color: '#c4c7d0', lineHeight: 1.5, padding: '8px 10px', background: '#12141f', borderRadius: 6 }}>
              {summary.summary || summary.top_insight || 'No summary available.'}
            </div>
          )}

          {!loading && briefing && (
            <div style={{ padding: '8px 10px', background: '#12141f', borderRadius: 6 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>📊 Daily Briefing</div>
              <div style={{ fontSize: 11, color: '#c4c7d0', lineHeight: 1.4 }}>{briefing.summary}</div>
              {briefing.priority_targets && briefing.priority_targets.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: '#7c8299', marginBottom: 3 }}>Priority targets:</div>
                  {briefing.priority_targets.slice(0, 3).map(t => (
                    <div key={t.id} style={{ fontSize: 11, color: '#c4c7d0', cursor: 'pointer', padding: '2px 0' }} onClick={() => navigate(`/target/${t.id}`)}>
                      • {t.name} ({t.confirmed} confirmed, {t.high_risk} high risk)
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {!loading && topTarget && (
            <div style={{
              padding: '10px 12px', borderRadius: 8,
              background: 'linear-gradient(135deg, rgba(34,197,94,0.15) 0%, rgba(74,222,128,0.1) 100%)',
              border: '1px solid rgba(34,197,94,0.3)',
              cursor: 'pointer',
            }}
              onClick={() => navigate(`/target/${topTarget.id}`)}
            >
              <div style={{ fontSize: 10, fontWeight: 700, color: '#22c55e', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>🏆 Quick Win</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e0e0e0' }}>{topTarget.name}</div>
              <div style={{ fontSize: 11, color: '#c4c7d0', marginTop: 2 }}>
                {topTarget.opportunities ?? 0} opportunities — click to investigate
              </div>
            </div>
          )}

          {!loading && bounty && (
            <div style={{ padding: '8px 10px', background: '#12141f', borderRadius: 6 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>💰 Bounty Potential</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#fbbf24' }}>
                ${bounty.payout_estimate.moderate_usd.toLocaleString()}
              </div>
              <div style={{ fontSize: 10, color: '#7c8299' }}>
                Range: ${bounty.payout_estimate.conservative_usd.toLocaleString()} – ${bounty.payout_estimate.optimistic_usd.toLocaleString()}
              </div>
              <div style={{ fontSize: 11, color: '#c4c7d0', marginTop: 4, lineHeight: 1.4 }}>
                {bounty.recommended_focus}
              </div>
            </div>
          )}

          {context && (
            <div style={{ fontSize: 11, color: '#7c8299', fontStyle: 'italic', padding: '4px 0' }}>
              {context}
            </div>
          )}

          {!loading && insights.length > 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>Key Insights</div>
              {insights.map((insight, i) => (
                <div key={insight.id || i} style={{
                  padding: '6px 8px', fontSize: 11, color: '#c4c7d0', lineHeight: 1.4,
                  borderLeft: `2px solid ${insight.severity === 'high' || insight.severity === 'critical' ? '#ef4444' : '#f59e0b'}`,
                  marginBottom: 4,
                }}>
                  {insight.title || insight.description}
                </div>
              ))}
            </div>
          )}

          {!loading && recommendations.length > 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>Recommendations</div>
              {recommendations.map((rec, i) => (
                <div key={i} style={{
                  padding: '6px 8px', fontSize: 11, color: '#c4c7d0',
                  display: 'flex', gap: 6, alignItems: 'flex-start',
                  marginBottom: 4,
                }}>
                  <span style={{ color: rec.priority === 'high' ? '#ef4444' : '#f59e0b' }}>•</span>
                  <span>{rec.action} {rec.endpoint ? `— ${rec.endpoint}` : ''}</span>
                </div>
              ))}
            </div>
          )}

          {chips.length > 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>Quick Actions</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {chips.map((s, i) => (
                  <button
                    key={i}
                    onClick={s.action}
                    style={{
                      padding: '5px 10px', borderRadius: 16, border: '1px solid #2a2e3d',
                      background: '#12141f', color: '#c4c7d0', fontSize: 11, cursor: 'pointer',
                      display: 'flex', alignItems: 'center', gap: 4, transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = '#7c3aed'; e.currentTarget.style.background = '#1e2230'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2e3d'; e.currentTarget.style.background = '#12141f'; }}
                  >
                    <span>{s.icon}</span>
                    <span>{s.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
