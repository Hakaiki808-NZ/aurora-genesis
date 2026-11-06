(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let config = null, token = '', busy = false;
  const base64url = bytes => btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/g,'');
  function random() {const b = new Uint8Array(32); crypto.getRandomValues(b); return base64url(b);}
  async function challenge(v) {const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(v));return base64url(new Uint8Array(hash));}
  function say(text) {$('status').textContent=String(text);}
  function msg(role, text) {
    const div=document.createElement('div');
    div.className='bubble '+role;
    div.textContent=text; // Never parse or inject model content as HTML.
    $('messages').appendChild(div);
    div.scrollIntoView({block:'end',behavior:'smooth'});
  }
  function loggedIn(ok) {
    $('login').hidden=ok; $('logout').hidden=!ok; $('send').disabled=!ok;
    say(ok ? 'Authenticated · Genesis deterministic test model · Aurora not attached' : 'Please sign in to run a test.');
  }
  async function login() {
    if(!config) {say('Configuration unavailable.');return;}
    const verifier=random(), state=random();
    sessionStorage.setItem('kyro_pkce', verifier);
    sessionStorage.setItem('kyro_state', state);
    const url=new URL(config.cognitoDomain+'/oauth2/authorize');
    url.searchParams.set('client_id',config.clientId);
    url.searchParams.set('response_type','code');
    url.searchParams.set('scope','openid email profile aws.cognito.signin.user.admin');
    url.searchParams.set('redirect_uri',config.redirectUri);
    url.searchParams.set('code_challenge_method','S256');
    url.searchParams.set('code_challenge',await challenge(verifier));
    url.searchParams.set('state',state);
    location.assign(url.toString());
  }
  async function callback() {
    const args=new URLSearchParams(location.search);
    if(args.has('error')) {history.replaceState({},'', '/');throw Error('Sign-in was not completed.');}
    if(!args.has('code')) return;
    const state=sessionStorage.getItem('kyro_state'), verifier=sessionStorage.getItem('kyro_pkce');
    history.replaceState({},'', '/');
    if(!state || args.get('state')!==state || !verifier) throw Error('Sign-in state mismatch. Retry.');
    sessionStorage.removeItem('kyro_state');sessionStorage.removeItem('kyro_pkce');
    const form=new URLSearchParams({grant_type:'authorization_code',client_id:config.clientId,code:args.get('code'),redirect_uri:config.redirectUri,code_verifier:verifier});
    const r=await fetch(config.cognitoDomain+'/oauth2/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:form});
    if(!r.ok) throw Error('Token exchange failed ('+r.status+').');
    const payload=await r.json();
    if(typeof payload.access_token!=='string') throw Error('Authentication token missing.');
    token=payload.access_token;
    sessionStorage.setItem('kyro_access',token);
    sessionStorage.setItem('kyro_expires',String(Date.now()+Math.min(payload.expires_in||3600,3600)*1000));
  }
  async function api(path,opts={}) {
    if(!token)throw Error('Sign in first.');
    const r=await fetch(config.apiUrl+path,{...opts,headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json'}});
    if(r.status===401||r.status===403){token='';sessionStorage.removeItem('kyro_access');sessionStorage.removeItem('kyro_expires');loggedIn(false);throw Error('Session expired or not authorized. Sign in again.');}
    const out=await r.json().catch(()=>({}));
    if(!r.ok)throw Error(String(out.error||'Service error')+' ('+r.status+').');
    return out;
  }
  $('login').addEventListener('click',()=>login().catch(e=>say(e.message)));
  $('logout').addEventListener('click',()=>{
    token='';sessionStorage.removeItem('kyro_access');sessionStorage.removeItem('kyro_expires');
    loggedIn(false);
    // Clear the application token; Cognito hosted sign-in cookie may remain until its own logout.
    if(config){const u=new URL(config.cognitoDomain+'/logout');u.searchParams.set('client_id',config.clientId);u.searchParams.set('logout_uri',config.redirectUri);location.assign(u.toString());}
  });
  $('chat-form').addEventListener('submit',async e=>{
    e.preventDefault();if(busy||!token)return;
    const txt=$('message').value.trim();if(!txt)return;
    busy=true;$('send').disabled=true; $('message').value='';
    msg('user',txt);
    try{const res=await api('/api/chat',{method:'POST',body:JSON.stringify({message:txt})});msg('assistant',String(res.answer||'No response'));}
    catch(err){msg('assistant','Test error: '+err.message);}
    finally{busy=false;$('send').disabled=!token;}
  });
  (async ()=>{
    try{
      const r=await fetch('/config.json',{cache:'no-store'});if(!r.ok)throw Error('Configuration missing.');
      config=await r.json(); await callback();
      if(!token && sessionStorage.getItem('kyro_access') && Number(sessionStorage.getItem('kyro_expires')||0)>Date.now()) token=sessionStorage.getItem('kyro_access');
      if(token){
        const status=await api('/api/status');
        if(!status.model_health?.ok)throw Error('Genesis health checks are not passing.');
        loggedIn(true);
      }else loggedIn(false);
    }catch(e){token='';loggedIn(false);say(e.message);}
  })();
})();
