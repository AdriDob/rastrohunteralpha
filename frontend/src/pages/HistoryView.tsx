import { useExecutionDecisions, useExecutionInsights, useExecutionTrackerStats } from '../lib/query';
import { useIsMobile } from '../lib/useIsMobile';
import Panel from '../components/ui/Panel';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingState from '../components/ui/LoadingState';
import { ApiErrorFallback } from '../components/ui/GlobalErrorBoundaryUI';

export default function HistoryView() {
  const isMobile = useIsMobile();
  const { data: decisions, isLoading: decLoading, isError: decError, refetch: refetchDec } = useExecutionDecisions(20);
  const { data: insights, isLoading: insLoading } = useExecutionInsights(20);
  const { data: stats, isLoading: statsLoading } = useExecutionTrackerStats();

  const loading = decLoading || insLoading || statsLoading;

  if (loading) {
    return (
      <div style={{ maxWidth: 800, margin: '0 auto', padding: isMobile ? '16px' : '24px 16px' }}>
        <LoadingState count={2} type="card" />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: isMobile ? '16px 16px 80px' : '24px 16px' }}>
      <div style={{ marginBottom: isMobile ? 16 : 24 }}>
        <h1 style={{ fontSize: isMobile ? 28 : 22, fontWeight: 700, margin: 0, color: '#fff' }}>History</h1>
        <p style={{ margin: '4px 0 0', fontSize: isMobile ? 14 : 13, color: '#7c8299' }}>
          Decision memory · insight archive · full system record
        </p>
      </div>

      {stats && (
        <div style={{ display: 'flex', gap: isMobile ? 16 : 12, marginBottom: isMobile ? 16 : 20, fontSize: isMobile ? 13 : 12, color: '#7c8299' }}>
          <span>Executions: <strong style={{ color: '#e2e8f0' }}>{stats.total_executions}</strong></span>
        </div>
      )}

      {decError && <ApiErrorFallback onRetry={() => refetchDec()} />}

      {decisions && decisions.decisions.length > 0 && (
        <Panel title={`Decision Memory (${decisions.count})`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {decisions.decisions.slice(0, isMobile ? 5 : undefined).map((d) => {
              const det = d.details;
              return (
                <Card key={d.id} padding={isMobile ? 'md' : 'sm'} accent="none">
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: isMobile ? 14 : undefined }}>
                      {det?.action || d.key}
                    </span>
                    <Badge
                      text={det?.outcome || 'pending'}
                      variant={det?.outcome === 'success' ? 'tier' : det?.outcome === 'error' ? 'severity' : 'default'}
                      color={det?.outcome === 'success' ? '#22c55e' : det?.outcome === 'error' ? '#ef4444' : undefined}
                    />
                  </div>
                  {det?.reason && <div style={{ color: '#7c8299', fontSize: isMobile ? 13 : undefined }}>{det.reason}</div>}
                  <div style={{ color: '#4b5563', marginTop: 2, fontSize: isMobile ? 12 : undefined }}>
                    confidence: {det?.confidence?.toFixed(2)} · {det?.source || 'system'}
                  </div>
                </Card>
              );
            })}
            {isMobile && decisions.decisions.length > 5 && (
              <details>
                <summary style={{
                  fontSize: 13, color: '#7c8299', cursor: 'pointer',
                  fontWeight: 600, padding: '8px 0', minHeight: 44,
                }}>
                  Show {decisions.decisions.length - 5} more
                </summary>
                {decisions.decisions.slice(5).map((d) => {
                  const det = d.details;
                  return (
                    <Card key={d.id} padding="md" accent="none" style={{ marginTop: 4 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                        <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{det?.action || d.key}</span>
                        <Badge text={det?.outcome || 'pending'} variant={det?.outcome === 'success' ? 'tier' : 'default'} />
                      </div>
                      {det?.reason && <div style={{ color: '#7c8299' }}>{det.reason}</div>}
                    </Card>
                  );
                })}
              </details>
            )}
          </div>
        </Panel>
      )}

      {insights && insights.insights.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <Panel title={`Insight Archive (${insights.count})`}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {insights.insights.slice(0, isMobile ? 5 : undefined).map((ins) => {
                const det = ins.details;
                return (
                  <Card key={ins.id} padding={isMobile ? 'md' : 'sm'} accent="none">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: isMobile ? 14 : undefined }}>
                        {det?.title || ins.key}
                      </span>
                      <Badge
                        text={det?.severity || 'info'}
                        variant={det?.severity === 'critical' ? 'severity' : 'default'}
                        color={det?.severity === 'critical' ? '#ef4444' : det?.severity === 'high' ? '#f97316' : undefined}
                      />
                    </div>
                    {det?.description && <div style={{ color: '#7c8299', fontSize: isMobile ? 13 : undefined }}>{det.description}</div>}
                    <div style={{ color: '#4b5563', marginTop: 2, fontSize: isMobile ? 12 : undefined }}>
                      {det?.insight_type} · {det?.source}
                    </div>
                  </Card>
                );
              })}
              {isMobile && insights.insights.length > 5 && (
                <details>
                  <summary style={{
                    fontSize: 13, color: '#7c8299', cursor: 'pointer',
                    fontWeight: 600, padding: '8px 0', minHeight: 44,
                  }}>
                    Show {insights.insights.length - 5} more
                  </summary>
                  {insights.insights.slice(5).map((ins) => {
                    const det = ins.details;
                    return (
                      <Card key={ins.id} padding="md" accent="none" style={{ marginTop: 4 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                          <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{det?.title || ins.key}</span>
                          <Badge text={det?.severity || 'info'} variant="default" />
                        </div>
                        {det?.description && <div style={{ color: '#7c8299' }}>{det.description}</div>}
                      </Card>
                    );
                  })}
                </details>
              )}
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}
