// The service worker (public spec §8). Play needs the server, every move is checked there, so it
// caches only the static shell, for a fast start; pages and the socket always go to the network.
// When a page load fails it shows the offline page. No offline play.
const CACHE = {{ cache | tojson }};
const SHELL = {{ shell | tojson }};
const OFFLINE = {{ offline | tojson }};

self.addEventListener('install', (event) => {
  // Fetched past the HTTP cache, so a release never fills its cache with the last one's files.
  const fresh = SHELL.map((path) => new Request(path, { cache: 'reload' }));
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(fresh)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys()
    .then((names) => Promise.all(names.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== location.origin) return;
  // A media element's range request for a sound goes to the network: iOS Safari stalls on a
  // whole cached response where it asked for a part.
  if (request.headers.has('range')) return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE)
      .then((page) => page ?? Response.error())));
  } else if (SHELL.includes(url.pathname)) {
    event.respondWith(caches.match(url.pathname).then((hit) => hit ?? fetch(request)));
  }
});
