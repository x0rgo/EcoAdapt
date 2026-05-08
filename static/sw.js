// EcoAdapt service worker — handles push notifications.
// Kept minimal: no precache, no offline shell. The dashboard hits the
// network for everything; this file exists purely so we can receive push.

self.addEventListener("install", (e) => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (_) {}

  const title = data.title || "EcoAdapt";
  const body  = data.body  || "Plant update";
  const url   = data.url   || "/";
  const tag   = data.tag   || "ecoadapt";

  event.waitUntil(self.registration.showNotification(title, {
    body,
    tag,
    renotify: true,
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    data: { url },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) {
      if (c.url.includes(url) && "focus" in c) return c.focus();
    }
    if (self.clients.openWindow) return self.clients.openWindow(url);
  })());
});
