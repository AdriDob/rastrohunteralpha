import { useEffect, useState } from 'react';
import { onEvent, onStatus, connect, disconnect, subscribe } from '../lib/ws';
import type { WSStatus } from '../lib/ws';

export type { WSStatus };

export function useWSStatus(): WSStatus {
  const [status, setStatus] = useState<WSStatus>('disconnected');

  useEffect(() => {
    const unsub = onStatus(setStatus);
    return unsub;
  }, []);

  return status;
}

export function useWSEvent(
  eventPattern: string,
  handler: (payload: Record<string, unknown>, ts: number) => void,
  deps: unknown[] = [],
): void {
  useEffect(() => {
    subscribe(eventPattern);
    const unsub = onEvent((type, payload, ts) => {
      const pat = eventPattern.endsWith('*')
        ? eventPattern.slice(0, -1)
        : eventPattern;
      if (type.startsWith(pat)) {
        handler(payload, ts);
      }
    });
    return unsub;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventPattern, handler, ...deps]);
}

export function useWSConnection(autoConnect = true): void {
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect]);
}
