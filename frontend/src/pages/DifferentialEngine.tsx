import { useMemo } from 'react';
import { useDifferentialAnalysis } from '../lib/query';
import Panel from '../components/ui/Panel';
import Badge from '../components/ui/Badge';
import ScoreBar from '../components/ui/ScoreBar';
import { SkeletonPanel } from '../components/ui/Skeleton';
import type { DiffFinding } from '../types';

function DiffCard({ finding, index }: { finding: DiffFinding; index: number }) {
  return (
    <div style={{
      padding: '14px 16px', borderRadius: 8,
      background: '#1e2230', border: '1px solid #2a2e3d',
      transition: 'all 0.15s', marginBottom: 8,
    }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#7c3aed'; e.currentTarget.style.background = '#222639'; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2a2e3d'; e.currentTarget.style.background = '#1e2230'; }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: '#7c8299', fontWeight: 600 }}>#{index + 1}</span>
          <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e4e9' }}>{finding.title}</span>
          <Badge text={finding.risk_level} variant="severity" />
        </div>
        <Badge text={finding.category} color="#8b5cf6" />
      </div>
      <div style={{ fontSize: 12, color: '#c4c7d0', marginBottom: 8, lineHeight: 1.5 }}>
        {finding.description || finding.affected_objects}
      </div>
      <div style={{ display: 'flex', gap: 24, fontSize: 11, color: '#7c8299' }}>
        {finding.confidence !== undefined && (
          <div style={{ flex: 1 }}>
            <ScoreBar value={finding.confidence} max={1} label="Confidence" />
          </div>
        )}
        {finding.novelty_score !== undefined && (
          <div style={{ flex: 1 }}>
            <ScoreBar value={finding.novelty_score} max={1} label="Novelty" color="#a855f7" />
          </div>
        )}
        {finding.potential_roi !== undefined && (
          <div style={{ flex: 1 }}>
            <ScoreBar value={finding.potential_roi} max={1} label="ROI" color="#22c55e" />
          </div>
        )}
      </div>
      {finding.supporting_signals && finding.supporting_signals.length > 0 && (
        <div style={{ display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap' }}>
          {finding.supporting_signals.map((sig, i) => (
            <Badge key={i} text={sig} color="#6b7280" />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DifferentialEngine() {
  const { data, isLoading } = useDifferentialAnalysis();

  const sections = useMemo(() => {
    if (!data) return [];
    return [
      { title: 'New & Changed Endpoints', key: 'endpoint_differences' as const, icon: '🔀' },
      { title: 'Target Diffs', key: 'target_differences' as const, icon: '🎯' },
      { title: 'Historical Changes', key: 'historical_changes' as const, icon: '📜' },
      { title: 'Cross-Target Patterns', key: 'cross_target_patterns' as const, icon: '🔗' },
      { title: 'Interesting Anomalies', key: 'interesting_anomalies' as const, icon: '⚠️' },
    ];
  }, [data]);

  if (isLoading) {
    return (
      <div>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#fff' }}>Differential Engine</div>
          <div style={{ fontSize: 13, color: '#7c8299' }}>Analyzing changes and anomalies...</div>
        </div>
        <div style={{ display: 'grid', gap: 16 }}>
          {Array.from({ length: 3 }).map((_, i) => <SkeletonPanel key={i} />)}
        </div>
      </div>
    );
  }

  const findingsCount = sections.reduce((sum, s) => sum + (data?.[s.key]?.length ?? 0), 0);

  return (
    <div style={{ maxWidth: 1400 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Differential Engine</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>
          {data?.summary || 'Detecting changes and anomalies across targets'}
          {data?.confidence !== undefined && (
            <span style={{ marginLeft: 12 }}>
              · Confidence: <strong style={{ color: '#e2e4e9' }}>{(data.confidence * 100).toFixed(0)}%</strong>
            </span>
          )}
        </p>
      </div>

      {findingsCount === 0 && (
        <div style={{ textAlign: 'center', padding: 60, color: '#7c8299', background: '#1a1d29', borderRadius: 10, border: '1px solid #2a2e3d' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: '#e2e4e9' }}>No Diffs Detected</div>
          <div style={{ fontSize: 13, marginTop: 4 }}>Run scans to generate differential data</div>
        </div>
      )}

      {sections.map(({ title, key, icon }) => {
        const items = (data?.[key] as DiffFinding[]) ?? [];
        if (items.length === 0) return null;
        return (
          <Panel
            key={key}
            title={`${icon} ${title}`}
            subtitle={`${items.length} finding${items.length !== 1 ? 's' : ''}`}
            accent="#8b5cf6"
            style={{ marginBottom: 12 }}
          >
            {items.map((f: DiffFinding, i: number) => (
              <DiffCard key={f.title + i} finding={f} index={i} />
            ))}
          </Panel>
        );
      })}

      {data?.web3_differences && data.web3_differences.length > 0 && (
        <Panel
          title="🌐 Web3 Diffs"
          subtitle={`${data.web3_differences.length} finding${data.web3_differences.length !== 1 ? 's' : ''}`}
          accent="#a855f7"
        >
          {(data.web3_differences as DiffFinding[]).map((f: DiffFinding, i: number) => (
            <DiffCard key={`web3-${i}`} finding={f} index={i} />
          ))}
        </Panel>
      )}

      {!isLoading && !data && (
        <div style={{ textAlign: 'center', padding: 60, color: '#7c8299', background: '#1a1d29', borderRadius: 10, border: '1px solid #2a2e3d' }}>
          <div style={{ fontSize: 16, fontWeight: 600 }}>No differential data available</div>
        </div>
      )}
    </div>
  );
}
