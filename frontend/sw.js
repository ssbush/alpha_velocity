// AlphaVelocity Service Worker v3
// Strategy: stale-while-revalidate for JS/CSS, no API/offline caching.
// CACHE_NAME is intentionally bumped on each meaningful deploy so old caches
// are wiped on first activate. The /api/version endpoint drives the in-page
// "update available" banner without requiring a manual bump here.
const CACHE_NAME = 'alphavelocity-v3.0.0';

// Install: activate immediately, no precaching
self.addEventListener('install', event => {
  event.waitUntil(self.skipWaiting());
});

// Activate: delete all old caches, claim clients
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(names => Promise.all(
        names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n))
      ))
      .then(() => self.clients.claim())
  );
});

// Fetch: only intercept JS/CSS with stale-while-revalidate.
// HTML (/) is left alone — server sends Cache-Control: no-store so the browser
// always fetches it fresh without the SW touching it.
// API calls and everything else pass through unmodified.
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // App shell JS/CSS: serve cached copy instantly, refresh in background
  if (url.pathname.includes('/js/') || url.pathname.includes('/css/')) {
    event.respondWith(staleWhileRevalidate(event.request));
  }
  // All other requests: no SW interception — browser and server handle caching
});

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  // Always fetch from network in the background to keep cache fresh
  const networkFetch = fetch(request).then(response => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => null);

  // Return cached immediately if available, otherwise wait for network
  return cached || networkFetch;
}

// Message handler: SKIP_WAITING forces immediate activation of a waiting SW
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
