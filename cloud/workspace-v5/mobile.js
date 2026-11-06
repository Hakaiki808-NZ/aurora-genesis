'use strict';
/* Mobile navigation enhancement; does not handle authentication or store credentials. */
document.addEventListener('DOMContentLoaded',()=>{
  const drawer=document.querySelector('.side');
  const toggle=document.getElementById('mobile-projects');
  if(drawer&&toggle){
    const close=()=>{drawer.classList.remove('mobile-menu-open');toggle.setAttribute('aria-expanded','false');};
    toggle.addEventListener('click',()=>{
      const open=drawer.classList.toggle('mobile-menu-open');
      toggle.setAttribute('aria-expanded',String(open));
    });
    drawer.addEventListener('click',event=>{
      if(event.target.closest('[data-mode],button.project'))close();
    });
    document.addEventListener('keydown',event=>{if(event.key==='Escape')close();});
    const media=window.matchMedia('(max-width:760px)');
    media.addEventListener?.('change',()=>{if(!media.matches)close();});
  }
  if('serviceWorker' in navigator && window.isSecureContext){
    navigator.serviceWorker.register('/v3/service-worker.js',{scope:'/v3/'}).catch(()=>{});
  }
});
