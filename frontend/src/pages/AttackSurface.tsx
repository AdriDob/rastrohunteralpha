import { useState } from 'react';
import { useAttackSurfaces } from '../lib/query';
import { useStore } from '../lib/store';
import { useNavigate } from 'react-router-dom';
import DataTable from '../components/tables/DataTable';
import { createColumnHelper } from '@tanstack/react-table';
import type { Endpoint } from '../types';

const helper = createColumnHelper<Endpoint>();
const columns = [
  helper.accessor('path', { header: 'Path' }),
  helper.accessor('method', { header: 'Method' }),
  helper.accessor('risk_score', { header: 'Risk', cell: (c) => Math.round(c.getValue()) }),
  helper.accessor('vector', { header: 'Vector' }),
];

const selectStyle: React.CSSProperties = {
  background: '#161a26', border: '1px solid #2a2e3d', borderRadius: 6,
  padding: '10px 14px', color: '#e2e4e9', fontSize: 13, width: 300,
  outline: 'none', marginBottom: 16,
};

export default function AttackSurface() {
  const { data: surfaces } = useAttackSurfaces();
  const setSelectedEndpoint = useStore((s) => s.setSelectedEndpoint);
  const navigate = useNavigate();
  const [selected, setSelected] = useState('');

  const keys = surfaces ? Object.keys(surfaces) : [];
  const currentKey = selected || keys[0] || '';
  const currentEndpoints = surfaces?.[currentKey] ?? [];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: '#fff' }}>Attack Surface Map</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: '#7c8299' }}>Endpoints grouped by attack surface category</p>
      </div>

      <select
        value={currentKey}
        onChange={(e) => setSelected(e.target.value)}
        style={selectStyle}
      >
        {keys.map((k) => (
          <option key={k} value={k}>{k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
        ))}
      </select>

      <DataTable
        data={currentEndpoints as any}
        columns={columns as any}
        pageSize={15}
        onRowClick={(row) => {
          setSelectedEndpoint((row as any).id);
          navigate(`/endpoint/${(row as any).id}`);
        }}
      />
    </div>
  );
}
