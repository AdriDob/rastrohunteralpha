import { useState, useEffect } from 'react';
import { withCache } from './cache';

const CACHE_TTL = 5 * 60 * 1000;

export function useOfflineFallback<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl: number = CACHE_TTL,
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setOffline(false);

    withCache(key, fetcher, ttl)
      .then((result) => {
        if (cancelled) return;
        setData(result.data);
        setOffline(result.fromCache && !navigator.onLine);
      })
      .catch(() => {
        if (!cancelled) setOffline(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [key, fetcher, ttl]);

  return { data, loading, offline };
}

export function useOnlineStatus() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const go = () => setOnline(true);
    const goAway = () => setOnline(false);
    window.addEventListener('online', go);
    window.addEventListener('offline', goAway);
    return () => {
      window.removeEventListener('online', go);
      window.removeEventListener('offline', goAway);
    };
  }, []);
  return online;
}

export function useBackgroundDetector() {
  const [backgrounded, setBackgrounded] = useState(false);
  useEffect(() => {
    const handleVis = () => setBackgrounded(document.visibilityState === 'hidden');
    document.addEventListener('visibilitychange', handleVis);
    return () => document.removeEventListener('visibilitychange', handleVis);
  }, []);
  return backgrounded;
}
