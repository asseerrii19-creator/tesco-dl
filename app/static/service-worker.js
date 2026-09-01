const CACHE='tsco-platform-v2-shell';
const STATIC=['/static/styles.css','/static/app.js','/static/field-form.js','/static/manifest.webmanifest'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(STATIC)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  const request=event.request,url=new URL(request.url);
  if(request.method!=='GET'||url.origin!==location.origin)return;
  if(url.pathname.startsWith('/static/')){
    event.respondWith(caches.match(request).then(cached=>cached||fetch(request).then(response=>{const copy=response.clone();caches.open(CACHE).then(c=>c.put(request,copy));return response;})));
    return;
  }
  event.respondWith(fetch(request).then(response=>{if(response.ok&&url.pathname.startsWith('/field')){const copy=response.clone();caches.open(CACHE).then(c=>c.put(request,copy));}return response;}).catch(()=>caches.match(request).then(cached=>cached||new Response('<h1>Offline</h1><p>Open a previously loaded Field Sampling page to continue.</p>',{headers:{'Content-Type':'text/html'}}))));
});
