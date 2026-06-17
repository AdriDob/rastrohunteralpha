import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { connect, disconnect, onEvent } from '../lib/ws';
import { useStore } from '../lib/store';

const EVENT_QUERY_MAP: Record<string, string[]> = {
  'finding:': ['findings'],
  'target:': ['targets'],
  'evidence:': ['evidence'],
  'scan:': ['scans'],
  'report:': ['reports'],
  'opportunity:': ['opportunities'],
  'system:state:': ['system'],
  'pipeline:': ['pipeline'],
  'verdict:': ['verdicts'],
};

export default function WSBridge() {
  const queryClient = useQueryClient();
  const addRecentInvestigation = useStore(s => s.addRecentInvestigation);

  useEffect(() => {
    connect();

    const unsub = onEvent((type, payload) => {
      for (const [prefix, keys] of Object.entries(EVENT_QUERY_MAP)) {
        if (type.startsWith(prefix)) {
          for (const key of keys) {
            queryClient.invalidateQueries({ queryKey: [key] });
          }
        }
      }

      if (type === 'notification:new') {
        const store = useStore.getState();
        store.setNotifications([...(store.notifications || []), payload as any]);
        store.setUnreadCount((store.unreadCount || 0) + 1);
      }

      if (type === 'target:created' && payload?.id && payload?.name) {
        addRecentInvestigation(payload.id as number, payload.name as string);
      }
    });

    return () => {
      unsub();
      disconnect();
    };
  }, [queryClient, addRecentInvestigation]);

  return null;
}
