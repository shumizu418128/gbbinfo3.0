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

// ネットワーク優先の戦略に変更
workbox.routing.registerRoute(
    new RegExp('/*'),
    new workbox.strategies.NetworkFirst({
        cacheName: CACHE,
        plugins: [
            new workbox.expiration.ExpirationPlugin({
                maxEntries: 50,
                maxAgeSeconds: 30 * 24 * 60 * 60, // 30日間
            }),
        ],
    })
);

self.addEventListener('fetch', (event) => {
    // 特定のファイルをキャッシュする条件を追加
    const alwaysCacheFiles = ['/static/images/icon/icon-search.webp', '/static/images/icon/icon-close.webp', '/static/images/icon/icon-home.webp']; // 常にキャッシュするファイルのパス

    // リクエストされた URL がキャッシュ対象のファイルかどうかを確認
    const requestUrl = new URL(event.request.url);
    if (alwaysCacheFiles.includes(requestUrl.pathname)) {
        event.respondWith(caches.open(CACHE).then((cache) => {
            return cache.match(event.request).then((cachedResp) => {
                if (cachedResp) {
                    return cachedResp; // キャッシュがあれば返す
                }
                return fetch(event.request).then((networkResp) => {
                    cache.put(event.request, networkResp.clone()); // ネットワークから取得したレスポンスをキャッシュに保存
                    return networkResp;
                });
            });
        }));
    } else {
        // その他のリクエストは通常の処理を行う
        return fetch(event.request);
    }
});
