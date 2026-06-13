import { useEffect, useState } from 'react';
import { getOpportunityEVHRankings } from '../lib/api';
import Panel from './ui/Panel';
import Badge from './ui/Badge';
import type { OpportunityItem, EVHRanking } from '../types';

export default function EVHWidget() {
  const [data, setData] = useState<EVHRanking | null>(null);

  useEffect(() => {
    getOpportunityEVHRankings(10).then(setData).catch(() => {});
  }, []);

  const evhColor = (rating: string) => {
    switch (rating) {
      case 'high': return '#22c55e';
      case 'medium': return '#f59e0b';
      case 'low': return '#ef4444';
      default: return '#7c8299';
    }
  };

  return (
    <Panel
      title="Expected Value Per Hour"
      subtitle={data ? `Avg: $${data.summary.average_evh.toFixed(0)}/hr` : ''}
      accent="#22c55e"
      loading={!data}
      empty={!data?.rankings?.length}
      emptyMessage="No EVH data available yet"
    >
      {data?.summary && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <div style={{ flex: 1, textAlign: 'center', padding: '8px', borderRadius: 6, background: 'rgba(34,197,94,0.1)' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#22c55e' }}>{data.summary.high}</div>
            <div style={{ fontSize: 10, color: '#7c8299' }}>High</div>
          </div>
          <div style={{ flex: 1, textAlign: 'center', padding: '8px', borderRadius: 6, background: 'rgba(245,158,11,0.1)' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b' }}>{data.summary.medium}</div>
            <div style={{ fontSize: 10, color: '#7c8299' }}>Medium</div>
          </div>
          <div style={{ flex: 1, textAlign: 'center', padding: '8px', borderRadius: 6, background: 'rgba(239,68,68,0.1)' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#ef4444' }}>{data.summary.low}</div>
            <div style={{ fontSize: 10, color: '#7c8299' }}>Low</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {(data?.rankings ?? []).slice(0, 8).map((opp: OpportunityItem) => (
          <div
            key={opp.id}
            style={{
              padding: '8px 10px', borderRadius: 6,
              background: '#1e2230', border: '1px solid #2a2e3d',
              fontSize: 12, transition: 'all 0.15s',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#e2e4e9', fontWeight: 600, flex: 1 }}>{opp.name}</span>
              <span style={{ color: opp.evh ? evhColor(opp.evh.rating) : '#7c8299', fontWeight: 700, fontSize: 13 }}>
                ${opp.evh?.value.toFixed(0) ?? '?'}/hr
              </span>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 4, color: '#7c8299', fontSize: 10, alignItems: 'center' }}>
              <Badge text={opp.evh?.rating ?? 'unknown'} color={opp.evh ? evhColor(opp.evh.rating) : '#7c8299'} />
              <span>{opp.evh?.explanation ?? ''}</span>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
