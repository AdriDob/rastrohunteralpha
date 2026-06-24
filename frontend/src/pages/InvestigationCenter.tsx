import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInvestigations, useCreateInvestigation, useDeleteInvestigation } from '../lib/query';
import { useQueryClient } from '@tanstack/react-query';
import type { Investigation } from '../types';

const statusColors: Record<string, string> = {
  active: '#7c3aed',
  paused: '#f59e0b',
  completed: '#10b981',
  abandoned: '#ef4444',
};

export default function InvestigationCenter() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const { data: invRes } = useInvestigations(null, statusFilter);
  const createMutation = useCreateInvestigation();
  const deleteMutation = useDeleteInvestigation();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newTargetId, setNewTargetId] = useState('');

  const investigations = invRes?.items ?? [];

  const handleCreate = () => {
    const targetId = parseInt(newTargetId);
    if (!newName || isNaN(targetId)) return;
    createMutation.mutate(
      { target_id: targetId, name: newName },
      {
        onSuccess: () => {
          setShowCreate(false);
          setNewName('');
          setNewTargetId('');
          queryClient.invalidateQueries({ queryKey: ['investigations'] });
        },
        onError: () => {
          // creation failed silently
        },
      },
    );
  };

  const handleDelete = (id: number) => {
    if (!confirm('Delete this investigation?')) return;
    deleteMutation.mutate(id, {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: ['investigations'] }),
      onError: () => {
        // deletion failed silently
      },
    });
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#fff', margin: 0 }}>Investigation Center</h1>
        <button onClick={() => setShowCreate(true)} style={{
          background: '#7c3aed', border: 'none', color: '#fff', padding: '8px 20px',
          borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 500,
        }}>+ New Investigation</button>
      </div>

      {showCreate && (
        <div style={{ background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d', padding: 20, marginBottom: 20 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15, color: '#fff' }}>Create Investigation</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input placeholder="Investigation name" value={newName} onChange={e => setNewName(e.target.value)}
              style={{
                background: '#12141f', border: '1px solid #2a2e3d', borderRadius: 6, padding: '8px 12px',
                color: '#e2e4e9', fontSize: 13, outline: 'none',
              }} />
            <input placeholder="Target ID" type="number" value={newTargetId} onChange={e => setNewTargetId(e.target.value)}
              style={{
                background: '#12141f', border: '1px solid #2a2e3d', borderRadius: 6, padding: '8px 12px',
                color: '#e2e4e9', fontSize: 13, outline: 'none',
              }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={handleCreate} disabled={createMutation.isPending} style={{
                background: createMutation.isPending ? '#4a1d96' : '#7c3aed', border: 'none',
                color: '#fff', padding: '8px 20px', borderRadius: 6, cursor: 'pointer', fontSize: 13,
              }}>{createMutation.isPending ? 'Creating…' : 'Create'}</button>
              <button onClick={() => setShowCreate(false)} style={{
                background: 'none', border: '1px solid #2a2e3d', color: '#7c8299',
                padding: '8px 20px', borderRadius: 6, cursor: 'pointer', fontSize: 13,
              }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {['all', 'active', 'paused', 'completed', 'abandoned'].map(s => {
          const isAll = s === 'all';
          const isActive = isAll ? !statusFilter : statusFilter === s;
          return (
            <button key={s} onClick={() => setStatusFilter(isAll ? undefined : s)} style={{
              background: isActive ? '#7c3aed' : 'transparent',
              border: `1px solid ${isActive ? '#7c3aed' : '#2a2e3d'}`,
              color: isActive ? '#fff' : '#7c8299', padding: '4px 12px', borderRadius: 12,
              cursor: 'pointer', fontSize: 12, fontWeight: 500,
            }}>{s.charAt(0).toUpperCase() + s.slice(1)}</button>
          );
        })}
      </div>

      {investigations.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#7c8299', background: '#1a1d29', borderRadius: 8, border: '1px solid #2a2e3d' }}>
          <div style={{ fontSize: 28, marginBottom: 12 }}>◈</div>
          <p style={{ fontSize: 14, margin: 0 }}>No investigations yet.</p>
          <p style={{ fontSize: 12, margin: '8px 0 0', color: '#4a4f63' }}>Start from Mission Control or create one manually to get started.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {investigations.map((inv: Investigation) => {
            const statusColor = statusColors[inv.status] || '#7c8299';
            return (
              <div key={inv.id}
                onClick={() => navigate(`/investigation/${inv.id}`)}
                style={{
                  background: '#1e2230', borderRadius: 8, border: '1px solid #2a2e3d',
                  padding: '14px 20px', cursor: 'pointer', display: 'flex',
                  alignItems: 'center', justifyContent: 'space-between',
                  transition: 'border-color 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = '#7c3aed60'}
                onMouseLeave={e => e.currentTarget.style.borderColor = '#2a2e3d'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%', background: statusColor,
                    boxShadow: `0 0 4px ${statusColor}80`, flexShrink: 0,
                  }} />
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>{inv.name}</div>
                    <div style={{ fontSize: 11, color: '#7c8299', marginTop: 2 }}>
                      Target #{inv.target_id} · {inv.tags?.length ? inv.tags.join(', ') : 'no tags'}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{
                    fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
                    color: statusColor, background: `${statusColor}15`,
                    padding: '2px 8px', borderRadius: 8,
                  }}>{inv.status}</span>
                  <button onClick={e => { e.stopPropagation(); handleDelete(inv.id); }} style={{
                    background: 'none', border: 'none', color: '#7c8299', cursor: 'pointer',
                    fontSize: 14, padding: 2,
                  }}>✕</button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
