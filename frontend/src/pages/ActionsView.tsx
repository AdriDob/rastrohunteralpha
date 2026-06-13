import { useNavigate, useParams } from 'react-router-dom';
import { useActionList, useActionHistory, useExecutionTrackerStats } from '../lib/query';
import { useIsMobile } from '../lib/useIsMobile';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingState from '../components/ui/LoadingState';
import { ApiErrorFallback } from '../components/ui/GlobalErrorBoundaryUI';

export default function ActionsView() {
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const { id: targetId } = useParams();
  const { data: actions, isLoading: al, isError: ae, refetch: ra } = useActionList();
  const { data: history, isLoading: hl } = useActionHistory(20);
  const { data: stats, isLoading: sl } = useExecutionTrackerStats();

  const loading = al || hl || sl;

  if (loading) {
    return (
      <div style={{ maxWidth: 720, margin: '0 auto', padding: isMobile ? '16px' : '24px 16px' }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: isMobile ? 28 : 22, fontWeight: 700, margin: 0, color: '#fff' }}>Actions</h1>
        </div>
        <LoadingState count={3} type="list" />
      </div>
    );
  }

  if (ae) {
    return (
      <div style={{ maxWidth: 720, margin: '0 auto', padding: isMobile ? '16px' : '24px 16px' }}>
        <h1 style={{ fontSize: isMobile ? 28 : 22, fontWeight: 700, margin: '0 0 16px', color: '#fff' }}>Actions</h1>
        <ApiErrorFallback onRetry={() => ra()} />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: isMobile ? '16px 16px 80px' : '24px 16px' }}>
      <div style={{ marginBottom: isMobile ? 16 : 24 }}>
        <h1 style={{ fontSize: isMobile ? 28 : 22, fontWeight: 700, margin: 0, color: '#fff' }}>Actions</h1>
        <p style={{ margin: '4px 0 0', fontSize: isMobile ? 14 : 13, color: '#7c8299' }}>
          {targetId ? `Target #${targetId}` : 'Available system actions'}
        </p>
      </div>

      {stats && (
        <div style={{ display: 'flex', gap: isMobile ? 16 : 12, marginBottom: isMobile ? 16 : 20, fontSize: isMobile ? 13 : 12, color: '#7c8299', flexWrap: 'wrap' }}>
          <span>Executed: <strong style={{ color: '#e2e8f0' }}>{stats.total_executions}</strong></span>
          {Object.entries(stats.by_type || {}).slice(0, 3).map(([type, s]) => (
            <span key={type}>{type}: <strong style={{ color: '#e2e8f0' }}>{(s as any).count ?? s}</strong></span>
          ))}
        </div>
      )}

      {actions && actions.actions.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: isMobile ? 12 : 8 }}>
          <h2 style={{ fontSize: 11, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 4px' }}>
            Available Actions
          </h2>
          {actions.actions.map((action) => (
            <Card key={action.id} padding={isMobile ? 'lg' : 'md'} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              minHeight: isMobile ? 72 : undefined,
            }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                  <span style={{ fontWeight: 600, fontSize: isMobile ? 16 : 14, color: '#e2e4e9' }}>{action.label}</span>
                  <Badge text={action.action_type} variant="default" />
                </div>
                <div style={{ fontSize: isMobile ? 12 : 12, color: '#7c8299' }}>{action.id}</div>
              </div>
              <button
                onClick={e => { e.stopPropagation(); if (action.route) navigate(action.route); }}
                style={{
                  background: '#7c3aed', color: '#fff', border: 'none',
                  fontSize: isMobile ? 14 : 11, fontWeight: 600,
                  padding: isMobile ? '12px 24px' : '6px 14px', borderRadius: 6,
                  cursor: 'pointer', transition: 'all 0.12s',
                  minHeight: isMobile ? 44 : undefined, flexShrink: 0,
                }}
                onMouseEnter={e => { e.currentTarget.style.background = '#6d28d9'; }}
                onMouseLeave={e => { e.currentTarget.style.background = '#7c3aed'; }}
                onMouseDown={e => { e.currentTarget.style.transform = 'scale(0.95)'; }}
                onMouseUp={e => { e.currentTarget.style.transform = 'scale(1)'; }}
              >
                Execute
              </button>
            </Card>
          ))}
        </div>
      )}

      {actions && actions.actions.length === 0 && (
        <Card padding="md" accent="none" style={{ textAlign: 'center', padding: isMobile ? '28px' : undefined }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>◈</div>
          <div style={{ color: '#7c8299', fontSize: isMobile ? 15 : 13 }}>No actions available right now</div>
          <div style={{ fontSize: isMobile ? 13 : 11, marginTop: 6, color: '#4a4f63' }}>System is analyzing — check back shortly</div>
        </Card>
      )}

      {history && history.history.length > 0 && (
        <div style={{ marginTop: isMobile ? 28 : 24 }}>
          <h2 style={{
            fontSize: 11, fontWeight: 700, color: '#7c8299',
            textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 8px',
          }}>
            Recent
          </h2>
          <details>
            <summary style={{
              fontSize: isMobile ? 14 : 12, color: '#7c8299', cursor: 'pointer',
              fontWeight: 600, padding: isMobile ? '8px 0' : undefined,
              minHeight: isMobile ? 44 : undefined,
            }}>
              {history.history.length} entries
            </summary>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 8 }}>
              {history.history.slice(0, isMobile ? 10 : 5).map((entry, i) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: isMobile ? '10px 14px' : '8px 12px',
                  borderRadius: 8, background: '#1a1e2b',
                  border: '1px solid #2a2e3d',
                  fontSize: isMobile ? 13 : 12,
                  transition: 'background 0.12s',
                }}
                  onMouseEnter={e => { e.currentTarget.style.background = '#252836'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = '#1a1e2b'; }}
                >
                  <span style={{ color: '#e2e8f0' }}>{entry.label || entry.action_id}</span>
                  <span style={{
                    color: entry.status === 'error' ? '#ef4444'
                      : entry.status === 'completed' ? '#22c55e' : '#f59e0b',
                    fontWeight: 600, fontSize: isMobile ? 12 : 11,
                  }}>
                    {entry.status} · {entry.duration_ms?.toFixed(0)}ms
                  </span>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
