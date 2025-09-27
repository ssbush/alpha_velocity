// AlphaVelocity Service Worker
const CACHE_NAME = 'alphavelocity-v1.0.0';
const OFFLINE_URL = '/offline.html';

// Resources to cache immediately
const PRECACHE_URLS = [
  '/',
  '/css/styles.css',
  '/js/app.js',
  '/js/api.js',
  '/js/charts.js',
  '/manifest.json',
  'https://cdn.jsdelivr.net/npm/chart.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
];

// API endpoints to cache with network-first strategy
const API_CACHE_PATTERNS = [
  '/portfolio/analysis',
  '/categories',
  '/momentum/top/',
  '/watchlist'
];

// Install event - precache essential resources
self.addEventListener('install', event => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Precaching app shell...');
        return cache.addAll(PRECACHE_URLS);
      })
      .then(() => {
        console.log('[SW] Service worker installed successfully');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('[SW] Precaching failed:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== CACHE_NAME) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('[SW] Service worker activated');
        return self.clients.claim();
      })
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Handle different resource types with different strategies
  if (isAppShellRequest(request)) {
    // App shell: Cache first, fallback to network
    event.respondWith(cacheFirst(request));
  } else if (isApiRequest(request)) {
    // API requests: Network first, fallback to cache
    event.respondWith(networkFirst(request));
  } else if (isStaticAsset(request)) {
    // Static assets: Cache first
    event.respondWith(cacheFirst(request));
  } else {
    // Default: Network first
    event.respondWith(networkFirst(request));
  }
});

// Cache-first strategy (for app shell and static assets)
async function cacheFirst(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[SW] Cache-first failed:', error);
    return new Response('Offline', { status: 503 });
  }
}

// Network-first strategy (for API and dynamic content)
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      // Cache successful API responses
      if (isApiRequest(request)) {
        const cache = await caches.open(CACHE_NAME);
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    }

    // Network failed, try cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    return networkResponse;
  } catch (error) {
    console.error('[SW] Network-first failed, trying cache:', error);

    // Network completely failed, try cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Show offline page for navigation requests
    if (request.destination === 'document') {
      return caches.match(OFFLINE_URL) || new Response('Offline', {
        status: 503,
        headers: { 'Content-Type': 'text/plain' }
      });
    }

    return new Response('Offline', { status: 503 });
  }
}

// Helper functions to identify request types
function isAppShellRequest(request) {
  const url = new URL(request.url);
  return url.pathname === '/' ||
         url.pathname.endsWith('.html') ||
         url.pathname.includes('/css/') ||
         url.pathname.includes('/js/');
}

function isApiRequest(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith('/portfolio/') ||
         url.pathname.startsWith('/categories') ||
         url.pathname.startsWith('/momentum/') ||
         url.pathname.startsWith('/watchlist') ||
         url.pathname.startsWith('/cache/');
}

function isStaticAsset(request) {
  const url = new URL(request.url);
  return url.pathname.includes('/css/') ||
         url.pathname.includes('/js/') ||
         url.pathname.includes('/images/') ||
         url.pathname.includes('/fonts/') ||
         url.hostname.includes('googleapis.com') ||
         url.hostname.includes('cdn.jsdelivr.net');
}

// Background sync for offline actions
self.addEventListener('sync', event => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'portfolio-sync') {
    event.waitUntil(syncPortfolioData());
  }
});

async function syncPortfolioData() {
  try {
    console.log('[SW] Syncing portfolio data...');
    // Implement background sync logic here
    // This could include uploading cached portfolio changes
    // or refreshing stale data when connection is restored
  } catch (error) {
    console.error('[SW] Portfolio sync failed:', error);
  }
}

// Push notification handling
self.addEventListener('push', event => {
  console.log('[SW] Push notification received:', event);

  const options = {
    body: event.data ? event.data.text() : 'Portfolio update available',
    icon: '/icon-192.png',
    badge: '/badge-72.png',
    tag: 'portfolio-update',
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'view-portfolio',
        title: 'View Portfolio',
        icon: '/icon-view.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/icon-dismiss.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('AlphaVelocity', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification clicked:', event);

  event.notification.close();

  if (event.action === 'view-portfolio') {
    event.waitUntil(
      clients.openWindow('/?view=portfolio')
    );
  } else if (event.action === 'dismiss') {
    // Just close the notification
  } else {
    // Default action - open the app
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Message handling from main thread
self.addEventListener('message', event => {
  console.log('[SW] Message received:', event.data);

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CACHE_PORTFOLIO') {
    // Cache specific portfolio data
    cachePortfolioData(event.data.payload);
  }
});

async function cachePortfolioData(portfolioData) {
  try {
    const cache = await caches.open(CACHE_NAME);
    const response = new Response(JSON.stringify(portfolioData), {
      headers: { 'Content-Type': 'application/json' }
    });
    await cache.put('/offline-portfolio', response);
    console.log('[SW] Portfolio data cached for offline use');
  } catch (error) {
    console.error('[SW] Failed to cache portfolio data:', error);
  }
}

console.log('[SW] Service worker script loaded');