const DB_NAME = 'rastro-offline';
const DB_VERSION = 1;
const STALE_MS = 5 * 60 * 1000;

interface CacheEntry<T = unknown> {
  key: string;
  data: T;
  cachedAt: number;
  ttl: number;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains('intel')) {
        db.createObjectStore('intel', { keyPath: 'key' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function cacheSet<T>(key: string, data: T, ttl: number = STALE_MS): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction('intel', 'readwrite');
    tx.objectStore('intel').put({ key, data, cachedAt: Date.now(), ttl } satisfies CacheEntry<T>);
    tx.oncomplete = () => db.close();
  } catch {
    // IndexedDB unavailable — degrade gracefully
  }
}

export async function cacheGet<T>(key: string): Promise<{ data: T; stale: boolean } | null> {
  try {
    const db = await openDB();
    const tx = db.transaction('intel', 'readonly');
    const entry = await new Promise<CacheEntry<T> | undefined>((resolve, reject) => {
      const req = tx.objectStore('intel').get(key);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    db.close();
    if (!entry) return null;
    return {
      data: entry.data,
      stale: Date.now() - entry.cachedAt > entry.ttl,
    };
  } catch {
    return null;
  }
}

export async function cacheKeys(): Promise<string[]> {
  try {
    const db = await openDB();
    const tx = db.transaction('intel', 'readonly');
    const keys = await new Promise<string[]>((resolve, reject) => {
      const req = tx.objectStore('intel').getAllKeys();
      req.onsuccess = () => resolve(req.result as string[]);
      req.onerror = () => reject(req.error);
    });
    db.close();
    return keys;
  } catch {
    return [];
  }
}

export async function cacheClear(): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction('intel', 'readwrite');
    tx.objectStore('intel').clear();
    tx.oncomplete = () => db.close();
  } catch {
    // ignore
  }
}

export async function withCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl: number = STALE_MS,
): Promise<{ data: T; fromCache: boolean }> {
  const cached = await cacheGet<T>(key);
  if (cached && !cached.stale) {
    return { data: cached.data, fromCache: true };
  }
  try {
    const data = await fetcher();
    await cacheSet(key, data, ttl);
    return { data, fromCache: false };
  } catch {
    if (cached) {
      return { data: cached.data, fromCache: true };
    }
    throw new Error(`Offline: no cached data for ${key}`);
  }
}
