import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { connect, disconnect, onStatus, onEvent } from '../lib/ws';
import { useStore, useUI } from '../lib/store';

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
  const retryCount = useRef(0);
  const { addRecentInvestigation } = useUI();

  useEffect(() => {
    connect();

    const unsubStatus = onStatus((status) => {
      const store = useStore.getState();
      store.setWSConnected(status);
      if (status === 'connected') {
        retryCount.current = 0;
      } else if (status === 'disconnected' && retryCount.current > 0) {
        store.setWSRetries(retryCount.current);
      }
    });

    const unsubEvent = onEvent((type, payload, ts) => {
      const store = useStore.getState();
      store.setWSLastMessage({ type, payload, ts } as any);

      for (const [prefix, keys] of Object.entries(EVENT_QUERY_MAP)) {
        if (type.startsWith(prefix)) {
          for (const key of keys) {
            queryClient.invalidateQueries({ queryKey: [key] });
          }
        }
      }

      if (type === 'notification:new') {
        store.addNotification(payload as any);
      }

      if (type === 'target:created') {
        const id = payload?.id;
        const name = payload?.name;
        if (id && name) {
          addRecentInvestigation(id as number, name as string);
        }
      }
    });

    return () => {
      unsubStatus();
      unsubEvent();
      disconnect();
    };
  }, [queryClient, addRecentInvestigation]);

  return null;
}
