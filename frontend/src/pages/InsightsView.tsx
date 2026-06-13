import { useExecutionExplanations, useExecutionTraces, useExecutionInsights } from '../lib/query';
import { useIsMobile } from '../lib/useIsMobile';
import Panel from '../components/ui/Panel';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingState from '../components/ui/LoadingState';
import { ApiErrorFallback } from '../components/ui/GlobalErrorBoundaryUI';

export default function InsightsView() {
  const isMobile = useIsMobile();
  const { data: explanations, isLoading: explLoading, isError: explError, refetch: refetchExpl } = useExecutionExplanations(10);
  const { data: traces, isLoading: tracesLoading } = useExecutionTraces(10);
  const { data: insights, isLoading: insLoading } = useExecutionInsights(10);

  const loading = explLoading || tracesLoading || insLoading;

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
        <h1 style={{ fontSize: isMobile ? 28 : 22, fontWeight: 700, margin: 0, color: '#fff' }}>Insights</h1>
        <p style={{ margin: '4px 0 0', fontSize: isMobile ? 14 : 13, color: '#7c8299' }}>
          System explanations · decision traces · archived insights
        </p>
      </div>

      {insights && !isMobile && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 20, fontSize: 12, color: '#7c8299' }}>
          <span>Total: <strong style={{ color: '#e2e8f0' }}>{insights.count}</strong></span>
          {Object.entries(insights.by_type || {}).map(([type, cnt]) => (
            <span key={type}>{type}: <strong style={{ color: '#e2e8f0' }}>{cnt}</strong></span>
          ))}
        </div>
      )}

      {explError && <ApiErrorFallback onRetry={() => refetchExpl()} />}

      {explanations && explanations.explanations.length > 0 && (
        <Panel title={`Explanations (${explanations.count})`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {explanations.explanations.slice(0, isMobile ? 3 : undefined).map((exp) => (
              <Card key={exp.id} padding={isMobile ? 'md' : 'sm'} accent="none">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: isMobile ? 14 : undefined }}>{exp.action}</span>
                  <Badge text={exp.confidence.toFixed(2)} variant={exp.confidence > 0.7 ? 'tier' : 'default'} />
                </div>
                <div style={{ color: '#7c8299', marginBottom: 4, fontSize: isMobile ? 13 : undefined }}>{exp.summary}</div>
                {exp.reasoning_chain.length > 0 && (
                  <details>
                    <summary style={{
                      fontSize: isMobile ? 13 : 11, color: '#7c8299', cursor: 'pointer',
                      fontWeight: 600, userSelect: 'none',
                      minHeight: isMobile ? 44 : undefined,
                    }}>
                      Reasoning ({exp.reasoning_chain.length} steps)
                    </summary>
                    <div style={{
                      fontSize: isMobile ? 12 : 11, color: '#4b5563', display: 'flex',
                      flexDirection: 'column', gap: 2, marginTop: 6,
                    }}>
                      {exp.reasoning_chain.map((step, i) => (
                        <span key={i}>→ {step}</span>
                      ))}
                    </div>
                  </details>
                )}
              </Card>
            ))}
            {isMobile && explanations.explanations.length > 3 && (
              <details>
                <summary style={{
                  fontSize: 13, color: '#7c8299', cursor: 'pointer',
                  fontWeight: 600, padding: '8px 0', minHeight: 44,
                }}>
                  Show {explanations.explanations.length - 3} more
                </summary>
                {explanations.explanations.slice(3).map((exp) => (
                  <Card key={exp.id} padding="md" accent="none" style={{ marginTop: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 14 }}>{exp.action}</span>
                      <Badge text={exp.confidence.toFixed(2)} variant={exp.confidence > 0.7 ? 'tier' : 'default'} />
                    </div>
                    <div style={{ color: '#7c8299', marginBottom: 4, fontSize: 13 }}>{exp.summary}</div>
                    {exp.reasoning_chain.length > 0 && (
                      <details>
                        <summary style={{ fontSize: 13, color: '#7c8299', cursor: 'pointer', fontWeight: 600, minHeight: 44 }}>
                          Reasoning ({exp.reasoning_chain.length} steps)
                        </summary>
                        <div style={{ fontSize: 12, color: '#4b5563', display: 'flex', flexDirection: 'column', gap: 2, marginTop: 6 }}>
                          {exp.reasoning_chain.map((step, i) => <span key={i}>→ {step}</span>)}
                        </div>
                      </details>
                    )}
                  </Card>
                ))}
              </details>
            )}
          </div>
        </Panel>
      )}

      {traces && traces.traces.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <Panel title={`Decision Traces (${traces.count})`}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {traces.traces.slice(0, isMobile ? 3 : undefined).map((trace) => (
                <Card key={trace.trace_id} padding={isMobile ? 'md' : 'sm'} accent="none">
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: isMobile ? 14 : undefined }}>{trace.action}</span>
                    <span style={{ color: '#7c8299', fontSize: isMobile ? 12 : undefined }}>
                      {trace.steps.length} steps · {trace.total_duration_ms.toFixed(0)}ms
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {trace.steps.map((step, i) => (
                      <Badge key={i} text={step.name} variant="default" />
                    ))}
                  </div>
                </Card>
              ))}
              {isMobile && traces.traces.length > 3 && (
                <details>
                  <summary style={{
                    fontSize: 13, color: '#7c8299', cursor: 'pointer',
                    fontWeight: 600, padding: '8px 0', minHeight: 44,
                  }}>
                    Show {traces.traces.length - 3} more
                  </summary>
                  {traces.traces.slice(3).map((trace) => (
                    <Card key={trace.trace_id} padding="md" accent="none" style={{ marginTop: 6 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{trace.action}</span>
                        <span style={{ color: '#7c8299' }}>{trace.steps.length} steps · {trace.total_duration_ms.toFixed(0)}ms</span>
                      </div>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {trace.steps.map((step, i) => <Badge key={i} text={step.name} variant="default" />)}
                      </div>
                    </Card>
                  ))}
                </details>
              )}
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}
