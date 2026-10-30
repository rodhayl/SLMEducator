/**
 * Service Worker for SLM Educator
 * Provides offline caching for static assets and basic pages
 * Version: 1.0.2
 */

const CACHE_NAME = 'slm-educator-v5';
const OFFLINE_URL = '/404.html';

// Static assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/login.html',
    '/dashboard.html',
    '/404.html',
    '/static/css/main.css',
    '/static/js/auth.js',
    '/static/js/theme.js',
    '/static/js/i18n.js',
    '/static/js/dashboard.js',
    '/static/js/toast.js',
    '/static/js/modules/inbox.js'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing Service Worker...');
    event.waitUntil(
        (async () => {
            try {
                const cache = await caches.open(CACHE_NAME);
                console.log('[SW] Caching static assets');

                await Promise.allSettled(
                    STATIC_ASSETS.map(async (assetUrl) => {
                        try {
                            const request = new Request(assetUrl, { cache: 'reload' });
                            const response = await fetch(request);
                            if (!response.ok) {
                                throw new Error(`HTTP ${response.status} for ${assetUrl}`);
                            }
                            await cache.put(request, response.clone());
                        } catch (error) {
                            console.warn('[SW] Failed to cache:', assetUrl, error);
                        }
                    })
                );

                console.log('[SW] Install complete');
                await self.skipWaiting();
            } catch (error) {
                console.error('[SW] Install failed:', error);
            }
        })()
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating Service Worker...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => {
                        console.log('[SW] Deleting old cache:', name);
                        return caches.delete(name);
                    })
            );
        }).then(() => {
            console.log('[SW] Activation complete');
            return self.clients.claim();
        })
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip API requests - always go to network
    if (url.pathname.startsWith('/api/')) {
        return;
    }

    // For JS/CSS: Network first to avoid stale UI/auth logic after updates.
    if (url.pathname.startsWith('/static/js/') || url.pathname.startsWith('/static/css/')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    if (response.ok) {
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return response;
                })
                .catch(() => caches.match(request))
        );
        return;
    }

    // For HTML pages: Network first, cache fallback
    if (request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Cache successful responses
                    if (response.ok) {
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    // Offline - try cache, then offline page
                    return caches.match(request).then((cachedResponse) => {
                        return cachedResponse || caches.match(OFFLINE_URL);
                    });
                })
        );
        return;
    }

    // For static assets: Cache first, network fallback
    event.respondWith(
        caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }
            return fetch(request).then((response) => {
                // Cache successful responses for static assets
                if (response.ok && (url.pathname.startsWith('/static/') || url.pathname.endsWith('.html'))) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, responseClone);
                    });
                }
                return response;
            });
        }).catch(() => {
            // Return nothing for failed non-HTML requests
            return new Response('', { status: 503, statusText: 'Service Unavailable' });
        })
    );
});
