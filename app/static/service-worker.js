// This is the service worker with the combined offline experience (Offline page + Offline copy of pages)

const CACHE = "pwabuilder-offline-page";

importScripts('https://storage.googleapis.com/workbox-cdn/releases/5.1.2/workbox-sw.js');

const currentYear = new Date().getFullYear();
const offlineFallbackPage = `/${currentYear}/top`;

self.addEventListener("message", (event) => {
    if (event.data && event.data.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
});

self.addEventListener('install', async(event) => {
    event.waitUntil(
        caches.open(CACHE)
        .then((cache) => cache.add(offlineFallbackPage))
    );
});

if (workbox.navigationPreload.isSupported()) {
    workbox.navigationPreload.enable();
}

// HTML ナビゲーションはネットワーク優先（オフライン時はキャッシュ）
workbox.routing.registerRoute(
    ({ request }) => request.mode === 'navigate',
    new workbox.strategies.NetworkFirst({
        cacheName: `${CACHE}-pages`,
        plugins: [
            new workbox.expiration.ExpirationPlugin({
                maxEntries: 50,
                maxAgeSeconds: 30 * 24 * 60 * 60, // 30日間
            }),
        ],
    })
);

// 静的アセット（CSS/JS/画像など）はキャッシュ優先（StaleWhileRevalidate）
workbox.routing.registerRoute(
    ({ request, url }) =>
        url.origin === self.location.origin &&
        ['style', 'script', 'image', 'font'].includes(request.destination),
    new workbox.strategies.StaleWhileRevalidate({
        cacheName: `${CACHE}-static`,
        plugins: [
            new workbox.expiration.ExpirationPlugin({
                maxEntries: 100,
                maxAgeSeconds: 30 * 24 * 60 * 60, // 30日間
            }),
        ],
    })
);
