/* Service Worker: hält nur die Oberfläche offline bereit.
   Live-Daten (WebSocket, /hscl, /endpoints) laufen immer direkt zum HomeServer. */
const CACHE = "hs-visu-v10";
const SHELL = ["./", "./index.html", "./manifest.json", "./icon-192.png", "./icon-512.png", "./icon-180.png", "./icon-maskable-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin || url.search) return;
  const path = url.pathname.split("/").pop() || "index.html";
  if (!SHELL.some(s => s.endsWith(path))) return;          // alles andere (z. B. /hscl, /endpoints) nicht anfassen
  // Netz zuerst (damit Updates sofort ankommen), sonst Cache
  e.respondWith(
    fetch(e.request, { cache: "no-store" }).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
      .catch(() => caches.match(e.request).then(r => r || caches.match("./index.html")))
  );
});
