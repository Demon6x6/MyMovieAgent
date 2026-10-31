// Service worker minimo: rende l'app installabile, i dati arrivano sempre dalla rete
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
