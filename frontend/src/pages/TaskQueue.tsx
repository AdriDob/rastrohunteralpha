import { useEffect, useState } from 'react';
import { getTasks, createTask, updateTask, deleteTask } from '../lib/api';
import type { TaskItem } from '../types';

const PRIORITIES = ['low', 'medium', 'high', 'critical'] as const;
const STATUSES = ['pending', 'in_progress', 'waiting', 'completed'] as const;

export default function TaskQueue() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [filter, setFilter] = useState<string>('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('medium');
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async (status?: string) => {
    setLoading(true);
    try {
      const r = await getTasks(status || undefined);
      setTasks(r.items);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!title.trim()) return;
    try {
      await createTask(title.trim(), description.trim() || undefined, 'pending', priority);
      setTitle('');
      setDescription('');
      setShowForm(false);
      load(filter || undefined);
    } catch {}
  };

  const handleStatus = async (task: TaskItem, newStatus: string) => {
    try { await updateTask(task.id, { status: newStatus }); load(filter || undefined); } catch {}
  };

  const handleDelete = async (id: number) => {
    try { await deleteTask(id); load(filter || undefined); } catch {}
  };

  const priorityColor = (p: string) => {
    if (p === 'critical') return '#ef4444';
    if (p === 'high') return '#f97316';
    if (p === 'medium') return '#f59e0b';
    return '#6b7280';
  };

  const statusBadge = (s: string) => {
    const colors: Record<string, string> = {
      pending: '#4a4f63', in_progress: '#7c3aed', waiting: '#f59e0b', completed: '#22c55e',
    };
    return <span style={{ background: colors[s] || '#4a4f63', color: '#fff', fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10 }}>{s.replace('_', ' ')}</span>;
  };

  const filtered = filter ? tasks.filter(t => t.status === filter) : tasks;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>Task Queue</h1>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select value={filter} onChange={e => { setFilter(e.target.value); load(e.target.value || undefined); }}
            style={{ background: '#1a1d29', color: '#e0e0e0', border: '1px solid #2a2e3d', borderRadius: 6, padding: '6px 10px', fontSize: 13 }}>
            <option value="">All</option>
            {STATUSES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
          </select>
          <button onClick={() => setShowForm(!showForm)}
            style={{ background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
            + New Task
          </button>
        </div>
      </div>

      {showForm && (
        <div style={{ background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8, padding: 16, marginBottom: 20 }}>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Task title"
            style={{ width: '100%', background: '#12141f', color: '#e0e0e0', border: '1px solid #2a2e3d', borderRadius: 6, padding: '8px 12px', fontSize: 13, marginBottom: 8 }}
            autoFocus />
          <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Description (optional)"
            style={{ width: '100%', background: '#12141f', color: '#e0e0e0', border: '1px solid #2a2e3d', borderRadius: 6, padding: '8px 12px', fontSize: 13, marginBottom: 8, minHeight: 60, resize: 'vertical' }} />
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <select value={priority} onChange={e => setPriority(e.target.value)}
              style={{ background: '#12141f', color: '#e0e0e0', border: '1px solid #2a2e3d', borderRadius: 6, padding: '6px 10px', fontSize: 13 }}>
              {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <button onClick={handleCreate} style={{ background: '#22c55e', color: '#fff', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Create</button>
            <button onClick={() => setShowForm(false)} style={{ background: 'transparent', color: '#7c8299', border: '1px solid #2a2e3d', borderRadius: 6, padding: '6px 14px', fontSize: 13, cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ color: '#4a4f63', padding: 40, textAlign: 'center' }}>Loading...</div>
      ) : filtered.length === 0 ? (
        <div style={{ color: '#4a4f63', padding: 40, textAlign: 'center' }}>No tasks found. Create one to get started.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {filtered.map(task => (
            <div key={task.id} style={{
              background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8, padding: '12px 16px',
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: priorityColor(task.priority), flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 2 }}>
                  <span style={{ color: '#e0e0e0', fontWeight: 600, fontSize: 14 }}>{task.title}</span>
                  {statusBadge(task.status)}
                  <span style={{ color: '#4a4f63', fontSize: 11 }}>{task.priority}</span>
                </div>
                {task.description && <div style={{ color: '#7c8299', fontSize: 12, lineHeight: 1.4 }}>{task.description}</div>}
                {task.linked_type && (
                  <div style={{ color: '#6366f1', fontSize: 11, marginTop: 4 }}>
                    Linked to {task.linked_type} #{task.linked_id}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                {STATUSES.map(s => (
                  <button key={s} onClick={() => handleStatus(task, s)}
                    style={{
                      background: task.status === s ? '#7c3aed' : 'transparent',
                      color: task.status === s ? '#fff' : '#4a4f63',
                      border: '1px solid', borderColor: task.status === s ? '#7c3aed' : '#2a2e3d',
                      borderRadius: 4, padding: '2px 8px', fontSize: 11, cursor: 'pointer',
                    }}>
                    {s.replace('_', ' ')}
                  </button>
                ))}
                <button onClick={() => handleDelete(task.id)}
                  style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 14, padding: '0 4px' }}>✕</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
