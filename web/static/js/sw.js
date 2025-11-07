const CACHE = 'ak-helper-v8';
const PRECACHE = [
  '/',                 // app shell
  '/manifest.webmanifest',
  '/static/app.js',
  '/static/app.css',
  '/static/icon-192.png',
  '/static/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

function isApiRequest(url) {
  // List every dynamic/API route that must be fresh
  return (
    url.pathname === '/guest-users' ||
    url.pathname === '/members-users' ||
    url.pathname.startsWith('/invites') ||
    url.pathname === '/promote' ||
    url.pathname === '/demote'
  );
}

// Pages: network-first (fallback to cache)
// Static assets: stale-while-revalidate
// API: network-only (no cache)
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Only handle same-origin
  if (url.origin !== location.origin) return;

  // API must be fresh and bypass HTTP cache
  if (isApiRequest(url)) {
    event.respondWith(fetch(new Request(req, { cache: 'no-store' })));
    return;
  }

  // Navigations: network-first
  if (req.mode === 'navigate') {
    event.respondWith(fetch(req).catch(() => caches.match('/')));
    return;
  }

  // Static assets: SWR
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(req);
    const fetched = fetch(req)
      .then((res) => { cache.put(req, res.clone()); return res; })
      .catch(() => cached);
    return cached || fetched;
  })());
});
