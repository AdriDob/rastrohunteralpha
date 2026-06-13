import { useState } from 'react';
import { useRunHypotheses, useTargets } from '../lib/query';
import DataTable from '../components/tables/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import type { Hypothesis } from '../types';

const helper = createColumnHelper<Hypothesis>();
const columns = [
  helper.accessor('vulnerability_type', { header: 'Type' }),
  helper.accessor('endpoint.path', { header: 'Path', cell: (c) => (c.getValue() as string) || '(aggregate)' }),
  helper.accessor('priority_score', { header: 'Priority', cell: (c) => (c.getValue() as number).toFixed(1) }),
  helper.accessor('likelihood', { header: 'L', cell: (c) => (c.getValue() as number).toFixed(2) }),
  helper.accessor('impact', { header: 'I', cell: (c) => (c.getValue() as number).toFixed(2) }),
  helper.accessor('exploitability', { header: 'E', cell: (c) => (c.getValue() as number).toFixed(2) }),
  helper.accessor('confidence', { header: 'Confidence', cell: (c) => (c.getValue() as number).toFixed(2) }),
  helper.accessor('source', { header: 'Source' }),
  helper.accessor('vector', { header: 'Vector' }),
];

export default function HypothesisQueue() {
  const [targetId, setTargetId] = useState<number | null>(null);
  const { data: targetsRes } = useTargets();
  const { data: engineOutput, isFetching, error } = useRunHypotheses(targetId);

  const targets = targetsRes?.items ?? [];
  const hypotheses = engineOutput?.attack_queue ?? [];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Hypothesis Queue</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>
          Run the Hypothesis Engine against a target to generate and prioritize attack vectors
        </p>
      </div>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 20 }}>
        <select
          value={targetId ?? ''}
          onChange={(e) => setTargetId(e.target.value ? Number(e.target.value) : null)}
          style={{
            background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 6,
            padding: '8px 14px', color: '#e2e4e9', fontSize: 13, outline: 'none', minWidth: 200,
          }}
        >
          <option value="">Select a target…</option>
          {targets.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>

        {isFetching && <span style={{ color: '#a855f7', fontSize: 13 }}>Generating hypotheses…</span>}
        {error && <span style={{ color: '#ef4444', fontSize: 13 }}>{(error as Error).message}</span>}
      </div>

      {engineOutput && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
          <div style={statBoxStyle}>
            <span style={statValueStyle}>{engineOutput.total_hypotheses}</span>
            <span style={statLabelStyle}>Total Hypotheses</span>
          </div>
          {Object.entries(engineOutput.by_source).map(([src, count]) => (
            <div key={src} style={statBoxStyle}>
              <span style={statValueStyle}>{count}</span>
              <span style={statLabelStyle}>{src}</span>
            </div>
          ))}
        </div>
      )}

      {engineOutput?.top_priority && (
        <div style={{
          background: 'linear-gradient(135deg, #1e1b4b, #312e81)',
          border: '1px solid #4c1d95', borderRadius: 8,
          padding: '14px 18px', marginBottom: 20,
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#a78bfa', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
            Top Priority
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>
            [{engineOutput.top_priority.vulnerability_type}] {engineOutput.top_priority.reasoning}
          </div>
          <div style={{ fontSize: 12, color: '#c4c7d0', marginTop: 4 }}>
            Priority: {engineOutput.top_priority.priority_score.toFixed(1)} · L={engineOutput.top_priority.likelihood.toFixed(2)} · I={engineOutput.top_priority.impact.toFixed(2)} · E={engineOutput.top_priority.exploitability.toFixed(2)}
          </div>
        </div>
      )}

      <DataTable
        data={hypotheses as any}
        columns={columns as any}
        pageSize={25}
        filterable={false}
      />
    </div>
  );
}

const statBoxStyle: Record<string, string | number> = {
  background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8,
  padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: 2,
};
const statValueStyle: Record<string, string | number> = {
  fontSize: 20, fontWeight: 700, color: '#fff',
};
const statLabelStyle: Record<string, string | number> = {
  fontSize: 11, fontWeight: 500, color: '#7c8299', textTransform: 'uppercase', letterSpacing: 0.5,
};
