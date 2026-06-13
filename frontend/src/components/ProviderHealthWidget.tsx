import { useEffect, useState } from 'react';
import { getOpportunityOverview } from '../lib/api';
import Panel from './ui/Panel';
import type { OpportunityOverview } from '../types';

export default function ProviderHealthWidget() {
  const [overview, setOverview] = useState<OpportunityOverview | null>(null);

  useEffect(() => {
    getOpportunityOverview().then(setOverview).catch(() => {});
  }, []);

  const healthColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#22c55e';
      case 'degraded': return '#f59e0b';
      case 'down': return '#ef4444';
      default: return '#7c8299';
    }
  };

  const providers = overview?.providers ?? [];

  return (
    <Panel
      title="Discovery Sources"
      subtitle={providers.length > 0 ? `${providers.length} providers` : ''}
      accent="#3b82f6"
      loading={!overview}
      empty={!providers.length}
      emptyMessage="No discovery sources registered"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {providers.map((p) => (
          <div
            key={p.name}
            style={{
              padding: '8px 10px', borderRadius: 6,
              background: '#1e2230', border: '1px solid #2a2e3d',
              fontSize: 12, transition: 'all 0.15s',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#e2e4e9', fontWeight: 600 }}>{p.name}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: '#7c8299', fontSize: 10 }}>{p.opportunity_count} opps</span>
                <div
                  style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: healthColor(p.health_status ?? 'unknown'),
                  }}
                />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 2, color: '#7c8299', fontSize: 10 }}>
              <span>{p.category}</span>
              {p.last_refresh && <span>· Last: {new Date(p.last_refresh).toLocaleDateString()}</span>}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
