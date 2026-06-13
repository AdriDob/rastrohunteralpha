import { useNavigate } from 'react-router-dom';
import { useStore } from '../lib/store';
import type { OpportunityItem, Target, ScoreBreakdown, EVHData } from '../types';

interface MissionData {
  target?: Target;
  opportunity?: OpportunityItem;
  score: number;
  priority: string;
  estimatedRoi: number;
  estimatedEffort: string;
  confidence: number;
  reasoning: string[];
  recommendedAction: string;
  scoreBreakdown?: ScoreBreakdown | null;
  evh?: EVHData | null;
}

interface Props {
  data?: MissionData | null;
  loading?: boolean;
}

function MissionCard({ data }: { data: MissionData }) {
  const navigate = useNavigate();
  const { setSelectedTarget, addRecentInvestigation } = useStore();

  const handleStart = () => {
    if (data.target) {
      setSelectedTarget(data.target.id);
      addRecentInvestigation(data.target.id, data.target.name);
      navigate(`/target/${data.target.id}`);
    } else if (data.opportunity?.public_url) {
      window.open(data.opportunity.public_url, '_blank');
    }
  };

  const priorityColor = data.priority === 'critical' ? '#ef4444' : data.priority === 'high' ? '#22c55e' : data.priority === 'medium' ? '#f59e0b' : '#6b7280';

  return (
    <div style={{
      background: 'linear-gradient(135deg, #1e2230 0%, #252836 100%)',
      border: `1px solid ${priorityColor}33`,
      borderRadius: 12, padding: 24,
      display: 'flex', flexDirection: 'column', gap: 16,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 4 }}>
            Today's Mission
          </div>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#fff', lineHeight: 1.2 }}>
            {data.target?.name || data.opportunity?.name || 'No active mission'}
          </h2>
        </div>
        <div style={{
          padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 700,
          background: `${priorityColor}20`, color: priorityColor, border: `1px solid ${priorityColor}40`,
        }}>
          {data.priority.toUpperCase()}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        <div><span style={{ fontSize: 10, color: '#7c8299', display: 'block' }}>SCORE</span><span style={{ fontSize: 24, fontWeight: 800, color: priorityColor }}>{data.score.toFixed(2)}</span></div>
        <div><span style={{ fontSize: 10, color: '#7c8299', display: 'block' }}>EST. ROI</span><span style={{ fontSize: 20, fontWeight: 700, color: '#22c55e' }}>${data.estimatedRoi.toLocaleString()}</span></div>
        <div><span style={{ fontSize: 10, color: '#7c8299', display: 'block' }}>EFFORT</span><span style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b' }}>{data.estimatedEffort}</span></div>
        <div><span style={{ fontSize: 10, color: '#7c8299', display: 'block' }}>CONFIDENCE</span><span style={{ fontSize: 20, fontWeight: 700, color: '#6366f1' }}>{(data.confidence * 100).toFixed(0)}%</span></div>
        {data.evh && (
          <div><span style={{ fontSize: 10, color: '#7c8299', display: 'block' }}>EVH</span><span style={{ fontSize: 20, fontWeight: 700, color: data.evh.rating === 'high' ? '#22c55e' : data.evh.rating === 'medium' ? '#f59e0b' : '#ef4444' }}>${data.evh.value.toFixed(0)}/hr</span></div>
        )}
      </div>

      {/* Score Breakdown */}
      {data.scoreBreakdown && (
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>Score Breakdown</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
            {[
              { label: 'Reward', score: data.scoreBreakdown.reward_score, exp: data.scoreBreakdown.reward_explanation },
              { label: 'Competition', score: data.scoreBreakdown.competition_score, exp: data.scoreBreakdown.competition_explanation },
              { label: 'Discovery', score: data.scoreBreakdown.discovery_score, exp: data.scoreBreakdown.discovery_explanation },
              { label: 'Execution', score: data.scoreBreakdown.execution_score, exp: data.scoreBreakdown.execution_explanation },
              { label: 'Intelligence', score: data.scoreBreakdown.intelligence_score, exp: data.scoreBreakdown.intelligence_explanation },
              { label: 'Strategic', score: data.scoreBreakdown.strategic_score, exp: data.scoreBreakdown.strategic_explanation },
              { label: 'Confidence', score: data.scoreBreakdown.confidence_score, exp: data.scoreBreakdown.confidence_explanation },
            ].map((f) => (
              <div key={f.label} style={{
                padding: '5px 8px', borderRadius: 4, background: '#12141f',
                fontSize: 11, color: '#c4c7d0', display: 'flex', justifyContent: 'space-between',
              }}>
                <span>{f.label}</span>
                <span style={{ fontWeight: 700, color: f.score > 60 ? '#22c55e' : f.score > 35 ? '#f59e0b' : '#ef4444' }}>
                  {f.score.toFixed(0)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>Why this mission</div>
        <ul style={{ margin: 0, padding: '0 0 0 16px', color: '#c4c7d0', fontSize: 13, lineHeight: 1.6 }}>
          {data.reasoning.slice(0, 4).map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      </div>

      <button
        onClick={handleStart}
        style={{
          padding: '12px 24px', borderRadius: 8, border: 'none', cursor: 'pointer',
          fontSize: 14, fontWeight: 700, color: '#fff',
          background: '#7c3aed', transition: 'all 0.15s', width: '100%',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = '#6d28d9'; }}
        onMouseLeave={e => { e.currentTarget.style.background = '#7c3aed'; }}
      >
        {data.recommendedAction}
      </button>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div style={{
      background: '#1e2230', border: '1px solid #2a2e3d', borderRadius: 12, padding: 24,
      display: 'flex', flexDirection: 'column', gap: 16,
    }}>
      <div style={{ width: 120, height: 12, background: '#2a2e3d', borderRadius: 4 }} />
      <div style={{ width: 200, height: 24, background: '#2a2e3d', borderRadius: 6 }} />
      <div style={{ display: 'flex', gap: 20 }}>
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} style={{ width: 70, height: 48, background: '#2a2e3d', borderRadius: 6 }} />
        ))}
      </div>
      <div style={{ width: '100%', height: 60, background: '#2a2e3d', borderRadius: 8 }} />
      <div style={{ width: '100%', height: 44, background: '#2a2e3d', borderRadius: 8 }} />
    </div>
  );
}

export default function MissionWidget({ data, loading }: Props) {
  return (
    <div style={{ gridColumn: '1 / -1' }}>
      {loading ? <LoadingSkeleton /> : data ? <MissionCard data={data} /> : (
        <div style={{
          background: '#1e2230', border: '1px dashed #2a2e3d', borderRadius: 12, padding: 32,
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>🎯</div>
          <div style={{ color: '#7c8299', fontSize: 14, lineHeight: 1.5 }}>
            No active mission.<br />
            <span style={{ color: '#4a4f63' }}>Explore opportunities or open a target to begin investigating.</span>
          </div>
        </div>
      )}
    </div>
  );
}
