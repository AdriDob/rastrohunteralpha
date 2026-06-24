import { useEffect, useRef, useState } from 'react';
import { useDashboard } from '../lib/store';
import { useIsMobile } from '../lib/useIsMobile';
import { markNotificationRead, markAllNotificationsRead } from '../lib/api';

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#6b7280',
  low: '#4a4f63',
};

function priorityColor(priority?: string): string {
  return PRIORITY_COLORS[priority ?? 'medium'] ?? PRIORITY_COLORS.medium;
}

function typeGroup(type: string): string {
  if (type === 'finding_alert' || type === 'scan_complete') return 'Pipeline';
  if (type === 'opportunity' || type === 'opportunity_detected' || type === 'quick_win' || type === 'quick_win_found') return 'Opportunities';
  if (type === 'report_ready') return 'Reports';
  if (type === 'session_expired' || type === 'system' || type === 'system_health_alert') return 'System';
  if (type === 'assistant' || type === 'assistant_recommendation') return 'Assistant';
  return 'Other';
}

export default function NotificationsDropdown() {
  const { notifications, unreadCount, fetchNotifications, markRead, markAllRead } = useDashboard();
  const [open, setOpen] = useState(false);
  const [groupBy, setGroupBy] = useState(true);
  const ref = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobile();

  useEffect(() => {
    fetchNotifications(true);
    const id = setInterval(() => fetchNotifications(true), 30000);
    return () => clearInterval(id);
  }, [fetchNotifications]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleMarkRead = async (id: number) => {
    try { await markNotificationRead(id); markRead(id); } catch {}
  };

  const handleMarkAll = async () => {
    try { await markAllNotificationsRead(); markAllRead(); } catch {}
  };

  const typeIcon = (t: string, priority?: string) => {
    const icons: Record<string, string> = {
      scan_complete: '✓',
      finding_alert: '⚡',
      system: '⚙',
      system_health_alert: '💚',
      quick_win: '🏆',
      quick_win_found: '🏆',
      opportunity: '🎯',
      opportunity_detected: '🎯',
      report_ready: '📄',
      assistant: '🧠',
      assistant_recommendation: '🧠',
      session_expired: '🔴',
    };
    return icons[t] ?? (priority === 'critical' ? '🔴' : '●');
  };

  const grouped = groupBy
    ? notifications.reduce<Record<string, typeof notifications>>((acc, n) => {
        const g = typeGroup(n.type);
        (acc[g] ??= []).push(n);
        return acc;
      }, {})
    : { All: notifications };

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: 'transparent', border: 'none', color: '#7c8299', cursor: 'pointer',
          fontSize: 18, position: 'relative', padding: '4px 8px',
        }}
      >
        🔔
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute', top: 0, right: 2, background: '#ef4444', color: '#fff',
            fontSize: 10, borderRadius: 8, padding: '1px 5px', fontWeight: 700, lineHeight: '14px',
          }}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, width: isMobile ? '92vw' : 380, maxHeight: 460,
          background: '#1a1d29', border: '1px solid #2a2e3d', borderRadius: 8,
          overflow: 'hidden', zIndex: 1000, boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderBottom: '1px solid #2a2e3d' }}>
            <span style={{ fontWeight: 700, fontSize: 13, color: '#fff' }}>Notifications</span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setGroupBy(!groupBy)}
                style={{ background: 'none', border: 'none', color: '#7c3aed', cursor: 'pointer', fontSize: 11 }}
              >
                {groupBy ? 'Flat' : 'Group'}
              </button>
              {unreadCount > 0 && (
                <button onClick={handleMarkAll} style={{ background: 'none', border: 'none', color: '#7c3aed', cursor: 'pointer', fontSize: 12 }}>
                  Mark all read
                </button>
              )}
            </div>
          </div>
          <div style={{ overflowY: 'auto', maxHeight: 400 }}>
            {notifications.length === 0 ? (
              <div style={{ padding: 20, textAlign: 'center', color: '#4a4f63', fontSize: 13 }}>No unread notifications</div>
            ) : (
              Object.entries(grouped).map(([group, items]) => (
                <div key={group}>
                  {groupBy && (
                    <div style={{
                      padding: '6px 14px', fontSize: 10, fontWeight: 700, color: '#7c8299',
                      textTransform: 'uppercase', letterSpacing: 0.5, background: '#12141f',
                    }}>
                      {group} ({items.length})
                    </div>
                  )}
                  {items.map(n => {
                    const priColor = priorityColor((n as any).priority);
                    return (
                      <div
                        key={n.id}
                        onClick={() => handleMarkRead(n.id)}
                        style={{
                          padding: '10px 14px', borderBottom: '1px solid #2a2e3d', cursor: 'pointer',
                          display: 'flex', gap: 10, alignItems: 'flex-start', transition: 'background 0.1s',
                          borderLeft: `3px solid ${priColor}`,
                        }}
                        onMouseEnter={e => (e.currentTarget.style.background = '#252836')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                      >
                        <span style={{ fontSize: 14, marginTop: 2 }}>{typeIcon(n.type, (n as any).priority)}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ color: '#e0e0e0', fontSize: 13, lineHeight: 1.4, wordBreak: 'break-word' }}>{n.message}</div>
                          <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 4 }}>
                            <span style={{ color: priColor, fontSize: 10, fontWeight: 600, textTransform: 'uppercase' }}>
                              {(n as any).priority ?? 'medium'}
                            </span>
                            <span style={{ color: '#4a4f63', fontSize: 11 }}>
                              {new Date(n.created_at).toLocaleString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
