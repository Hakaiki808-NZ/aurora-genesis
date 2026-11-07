'use strict';
(() => {
  const button=document.getElementById('check-health');
  const output=document.getElementById('health-result');
  if(!button || !output) return;
  button.addEventListener('click',async () => {
    button.disabled=true;
    output.textContent='Checking live endpoint…';
    const controller=new AbortController();
    const abort=setTimeout(()=>controller.abort(),8000);
    try {
      const response=await fetch('https://ces52hcf3e.execute-api.ap-southeast-2.amazonaws.com/api/v3/health',{signal:controller.signal,cache:'no-store',credentials:'omit'});
      const body=await response.json().catch(()=>null);
      output.textContent=response.ok && (body?.ok===true || body?.state==='operational') ? 'API reachable · health check passed (HTTP '+response.status+').' : 'API returned HTTP '+response.status+' · application health not confirmed.';
    } catch(e) {
      output.textContent=e.name==='AbortError'?'Request timed out; reachability not confirmed.':'API could not be reached from this browser. Check connection, CORS and deployment.';
    } finally { clearTimeout(abort);button.disabled=false; }
  });
})();