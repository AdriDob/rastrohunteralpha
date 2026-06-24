import { useOnlineStatus, useBackgroundDetector } from './hooks';

const BACKOFF_BASE = 1000;
const BACKOFF_MAX = 30000;

export function exponentialBackoff(attempt: number): number {
  const delay = Math.min(BACKOFF_BASE * Math.pow(2, attempt), BACKOFF_MAX);
  return delay + Math.random() * 1000;
}

export function shouldSkipRefresh(
  backgrounded: boolean,
  online: boolean,
  batterySave: boolean,
): boolean {
  if (!online) return true;
  if (backgrounded && batterySave) return true;
  return false;
}

const pending: Array<{ url: string; init?: RequestInit; resolve: (v: unknown) => void; reject: (e: unknown) => void }> = [];
let batchTimer: ReturnType<typeof setTimeout> | null = null;

function flushBatch() {
  const batch = pending.splice(0);
  batchTimer = null;
  Promise.all(
    batch.map(({ url, init, resolve, reject }) =>
      fetch(url, init).then(resolve).catch(reject)
    )
  );
}

export function batchedFetch(url: string, init?: RequestInit, windowMs = 100): Promise<unknown> {
  return new Promise((resolve, reject) => {
    pending.push({ url, init, resolve, reject });
    if (!batchTimer) {
      batchTimer = setTimeout(flushBatch, windowMs);
    }
  });
}

type DebouncedFn<T> = (...args: unknown[]) => T;

export function createDebouncedRefresh<T>(
  fn: DebouncedFn<Promise<T>>,
  delayMs: number,
): DebouncedFn<Promise<T>> {
  let timer: ReturnType<typeof setTimeout> | null = null;

  return (...args: unknown[]): Promise<T> => {
    if (timer) clearTimeout(timer);
    return new Promise<T>((resolve, reject) => {
      timer = setTimeout(async () => {
        try {
          const result = await fn(...args);
          resolve(result);
        } catch (err) {
          reject(err);
        }
      }, delayMs);
    });
  };
}

export { useOnlineStatus, useBackgroundDetector };
