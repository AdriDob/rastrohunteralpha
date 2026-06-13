import { useIntelligenceHistory, useIntelligenceTrends, useIntelligenceRecommendations, useIntelligenceState } from '../lib/query';
import Panel from '../components/ui/Panel';
import Badge from '../components/ui/Badge';
import { SkeletonPanel } from '../components/ui/Skeleton';

export default function IntelligenceDashboard() {
  const { data: history, isLoading: histLoading } = useIntelligenceHistory();
  const { data: trends, isLoading: trendsLoading } = useIntelligenceTrends();
  const { data: recommendations, isLoading: recsLoading } = useIntelligenceRecommendations();
  const { data: state, isLoading: stateLoading } = useIntelligenceState();

  const loading = histLoading || trendsLoading || recsLoading || stateLoading;

  if (loading) {
    return (
      <div>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#fff' }}>Adaptive Intelligence</div>
          <div style={{ fontSize: 13, color: '#7c8299' }}>Analyzing patterns and trends...</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {Array.from({ length: 4 }).map((_, i) => <SkeletonPanel key={i} />)}
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1400 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Adaptive Intelligence</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>
          Historical trends · Emerging surfaces · Best performing targets
        </p>
      </div>

      {/* State / Metrics cards */}
      {state && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12, marginBottom: 20 }}>
          <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: '14px 18px' }}>
            <div style={{ fontSize: 10, color: '#7c8299', fontWeight: 600, textTransform: 'uppercase' }}>Patterns Learned</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#a855f7', marginTop: 4 }}>{state.total_patterns_learned}</div>
          </div>
          <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: '14px 18px' }}>
            <div style={{ fontSize: 10, color: '#7c8299', fontWeight: 600, textTransform: 'uppercase' }}>Recommendations</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#22c55e', marginTop: 4 }}>{state.total_recommendations_generated}</div>
          </div>
          <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: '14px 18px' }}>
            <div style={{ fontSize: 10, color: '#7c8299', fontWeight: 600, textTransform: 'uppercase' }}>Snapshots</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#3b82f6', marginTop: 4 }}>{state.total_snapshots_created}</div>
          </div>
          <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: '14px 18px' }}>
            <div style={{ fontSize: 10, color: '#7c8299', fontWeight: 600, textTransform: 'uppercase' }}>Analysis Time</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#eab308', marginTop: 4 }}>
              {state.total_analysis_time_ms > 1000
                ? `${(state.total_analysis_time_ms / 1000).toFixed(1)}s`
                : `${state.total_analysis_time_ms.toFixed(0)}ms`}
            </div>
          </div>
          {state.last_analysis && (
            <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: '14px 18px' }}>
              <div style={{ fontSize: 10, color: '#7c8299', fontWeight: 600, textTransform: 'uppercase' }}>Last Analysis</div>
              <div style={{ fontSize: 13, color: '#c4c7d0', marginTop: 4 }}>{new Date(state.last_analysis).toLocaleDateString()}</div>
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* Historical Trends */}
        <Panel
          title="📈 Historical Trends"
          subtitle="Emerging patterns and direction"
          accent="#8b5cf6"
          loading={trendsLoading}
          empty={!trends?.trends?.length}
          emptyMessage="No trend data available yet"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(trends?.trends ?? []).map((t: any, i: number) => (
              <div key={i} style={{
                padding: '10px 12px', borderRadius: 6,
                background: '#1e2230', border: '1px solid #2a2e3d',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e4e9' }}>{t.name}</span>
                  <Badge text={t.direction} color={t.direction === 'up' ? '#22c55e' : t.direction === 'down' ? '#ef4444' : '#eab308'} />
                </div>
                <div style={{ fontSize: 11, color: '#c4c7d0' }}>{t.description}</div>
                {t.magnitude !== undefined && (
                  <div style={{ fontSize: 11, color: '#7c8299', marginTop: 4 }}>
                    Magnitude: <strong style={{ color: '#e2e4e9' }}>{t.magnitude.toFixed(2)}</strong>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Panel>

        {/* Recommendations */}
        <Panel
          title="🎯 Top Recommendations"
          subtitle="Priority actions from intelligence"
          accent="#22c55e"
          loading={recsLoading}
          empty={!recommendations}
          emptyMessage="No recommendations generated yet"
        >
          {recommendations && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {/* Targets */}
              {(recommendations.targets ?? []).slice(0, 3).map((r: any, i: number) => (
                <div key={`t-${i}`} style={{ padding: '8px 12px', borderRadius: 6, background: '#1e2230', border: '1px solid #2a2e3d' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#e2e4e9' }}>🎯 {r.name}</div>
                  <div style={{ fontSize: 11, color: '#c4c7d0', marginTop: 2 }}>{r.reason}</div>
                </div>
              ))}

              {/* Surfaces */}
              {(recommendations.surfaces ?? []).slice(0, 3).map((r: any, i: number) => (
                <div key={`s-${i}`} style={{ padding: '8px 12px', borderRadius: 6, background: '#1e2230', border: '1px solid #2a2e3d' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#e2e4e9' }}>🔍 {r.surface}</div>
                  <div style={{ fontSize: 11, color: '#c4c7d0', marginTop: 2 }}>{r.reason}</div>
                </div>
              ))}

              {/* Quick wins */}
              {(recommendations.quick_wins ?? []).slice(0, 3).map((r: any, i: number) => (
                <div key={`q-${i}`} style={{ padding: '8px 12px', borderRadius: 6, background: '#1e2230', border: '1px solid #2a2e3d' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#e2e4e9' }}>⚡ {r.endpoint}</div>
                  <div style={{ fontSize: 11, color: '#c4c7d0', marginTop: 2 }}>{r.reason}</div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* History summary */}
      <Panel
        title="📚 Intelligence History"
        subtitle="Analysis summary"
        accent="#3b82f6"
        loading={histLoading}
        empty={!history}
        emptyMessage="No history available"
      >
        {history && (
          <div style={{ fontSize: 13, color: '#c4c7d0', lineHeight: 1.6 }}>
            {history.summary && <p style={{ margin: '0 0 12px' }}>{history.summary}</p>}
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              {history.total_targets !== undefined && (
                <Badge text={`${history.total_targets} targets`} color="#a855f7" size="md" />
              )}
              {history.total_endpoints !== undefined && (
                <Badge text={`${history.total_endpoints} endpoints`} color="#3b82f6" size="md" />
              )}
              {history.total_findings !== undefined && (
                <Badge text={`${history.total_findings} findings`} color="#f97316" size="md" />
              )}
              {history.total_patterns !== undefined && (
                <Badge text={`${history.total_patterns} patterns`} color="#22c55e" size="md" />
              )}
            </div>
            {history.generated_at && (
              <div style={{ fontSize: 11, color: '#7c8299', marginTop: 12 }}>
                Generated: {new Date(history.generated_at).toLocaleString()}
              </div>
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}
