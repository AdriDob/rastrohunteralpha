import { useEffect, useRef, useState } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import { useStore } from '../lib/store';
import { getNotifications, getOpportunityRecommendations, fetchJson } from '../lib/api';

const NOTIFICATION_CHECK_INTERVAL = 60000;
const DIGEST_POLL_INTERVAL = 15000;
const DEDUP_TOAST_WINDOW = 30000;

export function NotificationToaster() {
  return (
    <Toaster
      position="bottom-right"
      toastOptions={{
        duration: 5000,
        style: {
          background: '#1e2230',
          color: '#e0e0e0',
          border: '1px solid #2a2e3d',
          borderRadius: 8,
          fontSize: 13,
        },
        success: {
          iconTheme: { primary: '#22c55e', secondary: '#1e2230' },
        },
        error: {
          iconTheme: { primary: '#ef4444', secondary: '#1e2230' },
        },
      }}
    />
  );
}

const PRIORITY_CONFIG: Record<string, { style: Record<string, string>; defaultIcon: string }> = {
  critical: { style: { background: '#3b1111', border: '1px solid #ef4444' }, defaultIcon: '🔴' },
  high: { style: { background: '#3b2a0a', border: '1px solid #f59e0b' }, defaultIcon: '⚠️' },
  medium: { style: {}, defaultIcon: '●' },
  low: { style: { opacity: '0.7' }, defaultIcon: '○' },
};

function getToastStyle(priority?: string) {
  return PRIORITY_CONFIG[priority ?? 'medium']?.style ?? {};
}

function getToastIcon(n: { type: string; priority?: string }) {
  const typeIcons: Record<string, string> = {
    quick_win: '🏆',
    opportunity: '🎯',
    report_ready: '📄',
    session_expired: '🔴',
    assistant: '🧠',
    scan_complete: '✓',
    finding_alert: '⚡',
    system_health_alert: '💚',
    opportunity_detected: '🎯',
  };
  return typeIcons[n.type] ?? PRIORITY_CONFIG[n.priority ?? 'medium']?.defaultIcon ?? '●';
}

function showToast(item: { id: number; type: string; message: string; priority?: string }) {
  const toastId = `notif-${item.id}`;
  const icon = getToastIcon(item);
  const style = getToastStyle(item.priority);
  const isError = item.type === 'session_expired' || item.priority === 'critical';
  const isSuccess = item.type === 'quick_win' || item.type === 'opportunity';

  if (isError) {
    toast.error(item.message, { id: toastId, icon, style });
  } else if (isSuccess) {
    toast.success(item.message, { id: toastId, icon, style });
  } else {
    toast(item.message, { id: toastId, icon, style });
  }
}

export function useSmartNotifications() {
  const lastCheckRef = useRef(0);
  const shownIdsRef = useRef(new Set<number>());
  const { setNotifications, setUnreadCount } = useStore();
  const [digestMode, setDigestMode] = useState(false);

  // Poll digest endpoint when digest mode is active
  useEffect(() => {
    if (!digestMode) return;
    const checkDigest = () => {
      fetchJson<{ digest: Array<{ type: string; count: number; highest_priority: string; titles: string[] }> }>(
        '/notifications/digest'
      ).then(resp => {
        if (resp.digest && resp.digest.length > 0) {
          resp.digest.forEach(group => {
            const toastId = `digest-${group.type}`;
            const titleList = group.titles.slice(0, 2).join(', ');
            const msg = `${group.count}× ${group.type.replace(/_/g, ' ')}${titleList ? `: ${titleList}` : ''}`;
            const isCritical = group.highest_priority === 'critical';
            if (isCritical) {
              toast.error(msg, { id: toastId, duration: 8000, icon: '📋' });
            } else {
              toast(msg, { id: toastId, icon: '📋', duration: 6000 });
            }
          });
        }
      }).catch(() => {});
    };
    checkDigest();
    const id = setInterval(checkDigest, DIGEST_POLL_INTERVAL);
    return () => clearInterval(id);
  }, [digestMode]);

  // Main notification poll
  useEffect(() => {
    const check = () => {
      const now = Date.now();
      if (now - lastCheckRef.current < 30000) return;
      lastCheckRef.current = now;

      getNotifications(true).then(r => {
        const unread = r.items.filter(n => !n.is_read);
        if (unread.length > 0) {
          setNotifications(r.items);
          setUnreadCount(unread.length);

          // Dedup-aware toast: skip if same id shown within window
          unread.slice(0, 3).forEach(n => {
            if (shownIdsRef.current.has(n.id)) return;
            shownIdsRef.current.add(n.id);
            setTimeout(() => shownIdsRef.current.delete(n.id), DEDUP_TOAST_WINDOW);
            if (!digestMode) {
              showToast(n);
            }
          });
        }
      }).catch(() => {});

      getOpportunityRecommendations().then(recs => {
        const highValue = (recs.top_opportunities ?? []).filter(
          o => o.priority === 'critical' || o.priority === 'high'
        );
        if (highValue.length > 0) {
          const topOpp = highValue[0];
          toast.success(`New top opportunity: ${topOpp.name}`, {
            id: `opp-alert-${topOpp.id}`,
            icon: '🎯',
            duration: 8000,
          });
        }
      }).catch(() => {});
    };

    check();
    const interval = setInterval(check, NOTIFICATION_CHECK_INTERVAL);
    return () => clearInterval(interval);
  }, [setNotifications, setUnreadCount, digestMode]);

  return { digestMode, setDigestMode };
}
