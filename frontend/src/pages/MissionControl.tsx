import { useTargets, useEndpoints, useOpportunities } from '../lib/query';
import { useStore } from '../lib/store';
import { useNavigate } from 'react-router-dom';
import KPICard from '../components/layout/KPICard';
import DataTable from '../components/tables/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import type { Opportunity } from '../types';

const oppHelper = createColumnHelper<Opportunity>();
const oppColumns = [
  oppHelper.accessor('name', { header: 'Target' }),
  oppHelper.accessor('roi', { header: 'ROI', cell: (c) => c.getValue().toFixed(1) }),
  oppHelper.accessor('max_risk', { header: 'Risk', cell: (c) => Math.round(c.getValue()) }),
  oppHelper.accessor('endpoint_count', { header: 'Endpoints' }),
  oppHelper.accessor('finding_count', { header: 'Findings' }),
  oppHelper.accessor('estimated_payout', { header: 'Payout', cell: (c) => `$${c.getValue().toLocaleString()}` }),
  oppHelper.accessor('surfaces', { header: 'Surfaces', cell: (c) => (c.getValue() || []).join(', ') }),
];

export default function MissionControl() {
  const { data: targetsRes } = useTargets({ limit: 100 });
  const { data: endpointsRes } = useEndpoints(null, { limit: 500 });
  const { data: opportunitiesRes } = useOpportunities({ limit: 100 });
  const setSelectedTarget = useStore((s) => s.setSelectedTarget);
  const navigate = useNavigate();

  const targets = targetsRes?.items ?? [];
  const endpoints = endpointsRes?.items ?? [];
  const opportunities = opportunitiesRes?.items ?? [];
  const target = targets[0];
  const confirmed = target?.confirmed_findings ?? 0;
  const totalValue = target?.estimated_payout ?? 0;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Mission Control</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>High signal. Low noise. Maximum impact.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
        <KPICard label="Active Targets" value={targets.length} icon="🎯" accent="rgba(124,58,237,0.12)" />
        <KPICard label="High-Signal Endpoints" value={endpoints.filter((e) => e.risk_score > 50).length} icon="📊" accent="rgba(34,197,94,0.12)" />
        <KPICard label="Confirmed Findings" value={confirmed} icon="✅" accent="rgba(59,130,246,0.12)" />
        <KPICard label="Est. Total ROI" value={totalValue > 0 ? `$${totalValue.toLocaleString()}` : '$0'} icon="💰" accent="rgba(234,179,8,0.12)" />
        <KPICard label="Endpoints Mapped" value={endpoints.length} icon="🔍" accent="rgba(168,85,247,0.12)" />
      </div>

      <div style={{ marginBottom: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: '#fff' }}>Top Opportunities</h2>
        <p style={{ margin: '2px 0 0', fontSize: 12, color: '#7c8299' }}>Highest ROI targets — click any row to drill down</p>
      </div>

      {opportunities && (
        <DataTable
          data={opportunities as any}
          columns={oppColumns as any}
          pageSize={8}
          onRowClick={(row) => {
            setSelectedTarget((row as any).target_id);
            navigate(`/target/${(row as any).target_id}`);
          }}
        />
      )}
    </div>
  );
}
