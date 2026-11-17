// Nunca armazena páginas autenticadas, respostas da API ou dados financeiros.
const CACHE = 'financeiro-public-v1';
const PUBLIC = ['/static/icons/icon-192.png', '/static/icons/icon-512.png'];
self.addEventListener('install', event => {
    event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PUBLIC)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
    event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('financeiro-public-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin || event.request.method !== 'GET' || !PUBLIC.includes(url.pathname)) return;
    event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
});
