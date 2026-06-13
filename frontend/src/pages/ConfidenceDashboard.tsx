import { useMemo, useState } from 'react';
import { useConfidenceAudit } from '../lib/query';
import Panel from '../components/ui/Panel';
import Badge from '../components/ui/Badge';
import ScoreBar from '../components/ui/ScoreBar';
import { SkeletonPanel } from '../components/ui/Skeleton';
import type { ConfidenceAudit } from '../types';

function getTier(score: number): { label: string; color: string } {
  if (score >= 0.7) return { label: 'HIGH', color: '#22c55e' };
  if (score >= 0.4) return { label: 'MEDIUM', color: '#eab308' };
  return { label: 'LOW', color: '#ef4444' };
}

function AuditCard({ audit }: { audit: ConfidenceAudit }) {
  const tier = getTier(audit.overall_score);
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{
      padding: '12px 16px', borderRadius: 8,
      background: '#1e2230', border: `1px solid ${tier.color}30`,
      marginBottom: 8, transition: 'all 0.15s',
      cursor: 'pointer',
    }}
      onClick={() => setExpanded(!expanded)}
      onKeyDown={(e) => e.key === 'Enter' && setExpanded(!expanded)}
      tabIndex={0}
      role="button"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e4e9' }}>{audit.item_label}</span>
          <Badge text={tier.label} color={tier.color} />
        </div>
        <span style={{ fontSize: 11, color: '#7c8299' }}>{audit.item_type}</span>
      </div>

      <ScoreBar value={audit.overall_score} max={1} label="Overall Confidence" color={tier.color} />

      <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 11, color: '#7c8299' }}>
        <span>Historical: <strong style={{ color: '#e2e4e9' }}>{(audit.historical_influence * 100).toFixed(0)}%</strong></span>
        <span>Evidence: <strong style={{ color: '#e2e4e9' }}>{(audit.evidence_influence * 100).toFixed(0)}%</strong></span>
        <span>ROI: <strong style={{ color: '#e2e4e9' }}>{(audit.roi_influence * 100).toFixed(0)}%</strong></span>
      </div>

      {expanded && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #2a2e3d' }}>
          <div style={{ fontSize: 11, color: '#7c8299', marginBottom: 8, fontWeight: 600 }}>FACTORS</div>
          {audit.factors.map((f, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#c4c7d0', marginBottom: 2 }}>
                <span>{f.name}</span>
                <span style={{ fontWeight: 600 }}>{(f.value * f.weight).toFixed(3)}</span>
              </div>
              <ScoreBar value={f.value} max={1} label="" />
              <div style={{ fontSize: 9, color: '#7c8299' }}>{f.description}</div>
            </div>
          ))}
          {audit.reasoning_summary && (
            <div style={{ marginTop: 8, fontSize: 11, color: '#c4c7d0', fontStyle: 'italic' }}>
              {audit.reasoning_summary}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ConfidenceDashboard() {
  const [itemType, setItemType] = useState<'verdict' | 'finding'>('verdict');
  const { data, isLoading } = useConfidenceAudit(itemType, 50);

  const { highConf, medConf, lowConf } = useMemo(() => {
    const audits = data?.audits ?? [];
    return {
      highConf: audits.filter((a) => a.overall_score >= 0.7),
      medConf: audits.filter((a) => a.overall_score >= 0.4 && a.overall_score < 0.7),
      lowConf: audits.filter((a) => a.overall_score < 0.4),
    };
  }, [data]);

  if (isLoading) {
    return (
      <div>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#fff' }}>Confidence Dashboard</div>
          <div style={{ fontSize: 13, color: '#7c8299' }}>Loading confidence audits...</div>
        </div>
        <div style={{ display: 'grid', gap: 16 }}>
          {Array.from({ length: 3 }).map((_, i) => <SkeletonPanel key={i} />)}
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1400 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Confidence Dashboard</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>
          {data ? `${data.total_audited} items audited · Average: ${(data.average_confidence * 100).toFixed(1)}%` : 'No audits available'}
        </p>
      </div>

      {/* Type toggle */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <div
          onClick={() => setItemType('verdict')}
          onKeyDown={(e) => e.key === 'Enter' && setItemType('verdict')}
          tabIndex={0}
          role="button"
          style={{
            padding: '8px 20px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
            background: itemType === 'verdict' ? '#7c3aed' : '#1e2230',
            border: `1px solid ${itemType === 'verdict' ? '#7c3aed' : '#2a2e3d'}`,
            color: itemType === 'verdict' ? '#fff' : '#7c8299',
            transition: 'all 0.15s',
          }}
        >
          Verdicts
        </div>
        <div
          onClick={() => setItemType('finding')}
          onKeyDown={(e) => e.key === 'Enter' && setItemType('finding')}
          tabIndex={0}
          role="button"
          style={{
            padding: '8px 20px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
            background: itemType === 'finding' ? '#7c3aed' : '#1e2230',
            border: `1px solid ${itemType === 'finding' ? '#7c3aed' : '#2a2e3d'}`,
            color: itemType === 'finding' ? '#fff' : '#7c8299',
            transition: 'all 0.15s',
          }}
        >
          Findings
        </div>
      </div>

      {!data || data.audits.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#7c8299', background: '#1a1d29', borderRadius: 10, border: '1px solid #2a2e3d' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📊</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#e2e4e9' }}>No Confidence Data</div>
          <div style={{ fontSize: 13, marginTop: 4 }}>Run validations to generate confidence audits</div>
        </div>
      ) : (
        <>
          {/* Summary cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
            <div style={{
              background: 'rgba(34,197,94,0.08)', borderRadius: 8,
              border: '1px solid rgba(34,197,94,0.3)', padding: '14px 18px',
            }}>
              <div style={{ fontSize: 11, color: '#22c55e', fontWeight: 600, marginBottom: 4 }}>HIGH CONFIDENCE</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#22c55e' }}>{highConf.length}</div>
            </div>
            <div style={{
              background: 'rgba(234,179,8,0.08)', borderRadius: 8,
              border: '1px solid rgba(234,179,8,0.3)', padding: '14px 18px',
            }}>
              <div style={{ fontSize: 11, color: '#eab308', fontWeight: 600, marginBottom: 4 }}>MEDIUM CONFIDENCE</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#eab308' }}>{medConf.length}</div>
            </div>
            <div style={{
              background: 'rgba(239,68,68,0.08)', borderRadius: 8,
              border: '1px solid rgba(239,68,68,0.3)', padding: '14px 18px',
            }}>
              <div style={{ fontSize: 11, color: '#ef4444', fontWeight: 600, marginBottom: 4 }}>LOW CONFIDENCE</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#ef4444' }}>{lowConf.length}</div>
              {lowConf.length > 0 && (
                <div style={{ fontSize: 10, color: '#ef4444', marginTop: 4 }}>Needs manual review</div>
              )}
            </div>
          </div>

          {/* Low confidence items first (needs review) */}
          {lowConf.length > 0 && (
            <Panel
              title="⚠️ Needs Manual Review"
              subtitle={`${lowConf.length} items with low confidence`}
              accent="#ef4444"
            >
              {lowConf.map((a: ConfidenceAudit) => (
                <AuditCard key={a.item_id} audit={a} />
              ))}
            </Panel>
          )}

          {/* High confidence */}
          {highConf.length > 0 && (
            <Panel
              title="✅ High Confidence"
              subtitle={`${highConf.length} reliable items`}
              accent="#22c55e"
              collapsible
            >
              {highConf.map((a: ConfidenceAudit) => (
                <AuditCard key={a.item_id} audit={a} />
              ))}
            </Panel>
          )}

          {/* Medium confidence */}
          {medConf.length > 0 && (
            <Panel
              title="🔶 Medium Confidence"
              subtitle={`${medConf.length} items requiring human assessment`}
              accent="#eab308"
              collapsible
            >
              {medConf.map((a: ConfidenceAudit) => (
                <AuditCard key={a.item_id} audit={a} />
              ))}
            </Panel>
          )}
        </>
      )}
    </div>
  );
}
