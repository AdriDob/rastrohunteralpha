const CACHE_STATIC = 'rastro-static-v3';
const CACHE_API = 'rastro-api-v3';
const CACHE_INTEL = 'rastro-intel-v3';

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/favicon.svg',
];

const API_CACHE_PREFIX = '/api/';
const INTEL_ENDPOINTS = [
  '/api/mobile/dashboard',
  '/api/mobile/opportunities',
  '/api/mobile/quick-wins',
  '/api/mobile/assistant-summary',
  '/api/mobile/notifications',
  '/api/opportunity/overview',
  '/api/digest',
  '/api/overview',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_STATIC).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((k) => k !== CACHE_STATIC && k !== CACHE_API && k !== CACHE_INTEL)
          .map((k) => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

function isIntelEndpoint(url) {
  return INTEL_ENDPOINTS.some((ep) => url.includes(ep));
}

function isApiRequest(url) {
  return url.includes(API_CACHE_PREFIX);
}

function isStaticAsset(url) {
  return (
    STATIC_ASSETS.some((a) => url.endsWith(a)) ||
    url.match(/\.(js|css|woff2?|png|svg|ico|json)$/)
  );
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = request.url;

  // Never cache non-GET requests (POST, PUT, DELETE, etc.)
  // Cache API only supports GET requests.
  if (request.method !== 'GET') {
    event.respondWith(fetch(request));
    return;
  }

  if (isStaticAsset(url)) {
    event.respondWith(networkFirst(request, CACHE_STATIC));
    return;
  }

  if (isIntelEndpoint(url)) {
    event.respondWith(staleWhileRevalidate(request, CACHE_INTEL));
    return;
  }

  if (isApiRequest(url)) {
    event.respondWith(networkFirst(request, CACHE_API));
    return;
  }

  event.respondWith(networkFirst(request, CACHE_STATIC));
});

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok && request.method === 'GET') {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok && request.method === 'GET') {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ offline: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request)
    .then((response) => {
      if (response.ok && request.method === 'GET') cache.put(request, response.clone());
      return response;
    })
    .catch(() => cached);

  return cached || fetchPromise;
}

self.addEventListener('push', (event) => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    const title = data.title || 'Rastro';
    const options = {
      body: data.message || data.body || '',
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      data: { url: data.url || '/' },
      tag: data.tag || data.type || 'default',
      renotify: true,
    };
    event.waitUntil(self.registration.showNotification(title, options));
  } catch {
    event.waitUntil(
      self.registration.showNotification('Rastro', {
        body: event.data.text(),
        icon: '/icon-192.png',
      })
    );
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((windowClients) => {
      const focused = windowClients.find((c) => c.url === url && 'focus' in c);
      if (focused) return focused.focus();
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
