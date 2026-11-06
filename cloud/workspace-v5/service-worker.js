'use strict';
/* Static shell assets only. Never cache protected pages, API requests, auth redirects, or user data. */
const CACHE='kyro-v5-static-20261107-a';
const ALLOWED=new Set(['/v3/styles.css','/v3/light.css','/v3/mobile.css','/v3/preview.css','/v3/kyro-icon.svg']);
self.addEventListener('install',event=>{self.skipWaiting();});
self.addEventListener('activate',event=>{
  event.waitUntil((async()=>{for(const key of await caches.keys()){if(key.startsWith('kyro-v5-static-')&&key!==CACHE)await caches.delete(key);}await self.clients.claim();})());
});
self.addEventListener('fetch',event=>{
  const request=event.request;
  if(request.method!=='GET'||request.mode==='navigate')return;
  const url=new URL(request.url);
  if(url.origin!==self.location.origin||!ALLOWED.has(url.pathname))return;
  event.respondWith((async()=>{
    try{
      const response=await fetch(request);
      if(response.ok&&response.type==='basic'){const cache=await caches.open(CACHE);await cache.put(request,response.clone());}
      return response;
    }catch{
      const cached=await caches.match(request);
      return cached||Response.error();
    }
  })());
});
