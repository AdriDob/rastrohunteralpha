import { useNavigate } from 'react-router-dom';
import { useDailyBriefing } from '../lib/query';
import { useIsMobile } from '../lib/useIsMobile';
import Card from '../components/ui/Card';
import LoadingState from '../components/ui/LoadingState';
import { ApiErrorFallback } from '../components/ui/GlobalErrorBoundaryUI';

export default function DailyMode() {
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const { data, isLoading, isError, refetch } = useDailyBriefing();
  const briefing = data?.briefing ?? null;
  const showLoading = isLoading && !briefing;

  if (showLoading) {
    return (
      <div style={{ maxWidth: 600, margin: '0 auto', padding: isMobile ? '16px' : '24px 16px' }}>
        <LoadingState count={1} type="detail" />
        <div style={{ marginTop: 20 }}><LoadingState count={2} type="list" /></div>
      </div>
    );
  }

  if (isError && !briefing) {
    return (
      <div style={{ maxWidth: 600, margin: '0 auto', padding: isMobile ? '16px' : '24px 16px' }}>
        <Header />
        <ApiErrorFallback onRetry={() => refetch()} />
      </div>
    );
  }

  const topAction = briefing?.recommended_action;
  const opportunities = briefing?.opportunities?.slice(0, 2) ?? [];
  const risk = briefing?.critical_risk;
  const insight = briefing?.assistant_insight;
  const health = briefing?.system_health;

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: isMobile ? '16px 16px 80px' : '24px 16px' }}>
      <Header health={health} insight={insight} />

      {topAction && (
        <Card
          accent="primary"
          padding="lg"
          onClick={() => navigate(topAction.payload?.route ?? '/actions')}
          style={{ marginBottom: 20, minHeight: isMobile ? 160 : undefined }}
        >
          <div style={{
            position: 'absolute', top: -8, right: 16,
            background: '#7c3aed', color: '#fff',
            fontSize: isMobile ? 10 : 9, fontWeight: 700, padding: '3px 14px', borderRadius: 4,
            textTransform: 'uppercase', letterSpacing: 1,
          }}>
            Best Action
          </div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
            {topAction.action}
          </div>
          <div style={{ fontWeight: 700, fontSize: isMobile ? 20 : 18, color: '#fff', marginBottom: 6 }}>
            {topAction.label}
          </div>
          <div style={{ fontSize: isMobile ? 14 : 13, color: '#c4c7d0', lineHeight: 1.5 }}>
            {topAction.reason}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: isMobile ? 16 : 12 }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              background: 'rgba(124,58,237,0.3)', color: '#fff',
              fontSize: isMobile ? 13 : 11, fontWeight: 600,
              padding: isMobile ? '10px 24px' : '4px 12px', borderRadius: 6,
              minHeight: isMobile ? 44 : undefined,
            }}>
              Execute
            </span>
            <span style={{ fontSize: 10, color: '#7c8299' }}>
              {(topAction.confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
        </Card>
      )}

      {opportunities.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <h2 style={{ fontSize: 11, fontWeight: 700, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 1, margin: 0 }}>
            Next Actions
          </h2>
          {opportunities.map((o, i) => {
            return (
              <Card key={o.id ?? i} padding={isMobile ? 'lg' : 'md'} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                minHeight: isMobile ? 72 : undefined,
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: isMobile ? 16 : 14, color: '#e2e4e9' }}>{o.name}</div>
                  <div style={{ fontSize: 12, color: '#7c8299', marginTop: 3 }}>{o.category}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontWeight: 700, fontSize: isMobile ? 16 : 14, color: '#22c55e' }}>
                    ${o.estimated_payout?.toLocaleString() ?? 0}
                  </span>
                  <button
                    onClick={e => { e.stopPropagation(); navigate('/actions'); }}
                    style={{
                      background: '#7c3aed', color: '#fff', border: 'none',
                      fontSize: isMobile ? 14 : 11, fontWeight: 600,
                      padding: isMobile ? '12px 24px' : '4px 12px', borderRadius: 6,
                      cursor: 'pointer', transition: 'all 0.12s',
                      minHeight: isMobile ? 44 : undefined,
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = '#6d28d9'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = '#7c3aed'; }}
                    onMouseDown={e => { e.currentTarget.style.transform = 'scale(0.95)'; }}
                    onMouseUp={e => { e.currentTarget.style.transform = 'scale(1)'; }}
                  >
                    Execute
                  </button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {risk && (
        <Card
          accent="risk"
          padding="md"
          onClick={() => navigate('/insights')}
          style={{ marginTop: 20, minHeight: isMobile ? 60 : undefined }}
        >
          <div style={{ fontWeight: 700, fontSize: 11, color: '#ef4444', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            {risk.severity} Risk
          </div>
          <div style={{ fontWeight: 600, fontSize: isMobile ? 15 : 14, color: '#fff', marginTop: 4 }}>{risk.title}</div>
        </Card>
      )}

      {insight && (
        <details style={{ marginTop: 24, cursor: 'pointer' }}>
          <summary style={{
            fontSize: 11, fontWeight: 600, color: '#7c8299',
            textTransform: 'uppercase', letterSpacing: 1,
            padding: isMobile ? '8px 0' : undefined,
            minHeight: isMobile ? 44 : undefined,
          }}>
            System Insight
          </summary>
          <p style={{ fontSize: isMobile ? 14 : 13, color: '#7c8299', marginTop: 8, lineHeight: 1.5 }}>
            {insight.focus} — {insight.reason}
          </p>
        </details>
      )}
    </div>
  );
}

function Header({ health, insight }: { health?: any; insight?: any }) {
  const isMobile = useIsMobile();
  return (
    <div style={{ marginBottom: isMobile ? 16 : 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <h1 style={{ fontSize: isMobile ? 28 : 24, fontWeight: 700, margin: 0, color: '#fff' }}>Today</h1>
        {health && (
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            background: health.status === 'READY' ? '#22c55e'
              : health.status === 'DEGRADED' ? '#f59e0b' : '#ef4444',
            flexShrink: 0,
          }} />
        )}
      </div>
      <p style={{ margin: '4px 0 0', fontSize: isMobile ? 14 : 13, color: '#7c8299' }}>
        {insight?.system_state ?? 'System ready'}
      </p>
    </div>
  );
}
