'use strict';
// Kyro temporary chat: authenticated view of existing Kyro conversation endpoints.
// No engine/tool privileges are granted by the browser application.
const CONFIG=Object.freeze({
  api:'https://ces52hcf3e.execute-api.ap-southeast-2.amazonaws.com',
  client:'68i1h2nqhvsjruneo12k0u3ahm',
  auth:'https://kyro-v4-private-179502447662.auth.ap-southeast-2.amazoncognito.com',
  callback:'https://d3j65cc3p66kzr.cloudfront.net/temp-chat/index.html',
  issuer:'https://cognito-idp.ap-southeast-2.amazonaws.com/ap-southeast-2_Pq71kumUV'
});
const S={token:null,refresh:null,expires:0,conversations:[],current:null,messages:[],busy:false,pendingUser:null,account:null,sidebarOpen:true,speech:null};
const $=id=>document.getElementById(id);
const el=(tag,cls,txt)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=String(txt);return n;};
const b64url=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
let toastTimer=null;
function notify(message){const n=$('toast');n.textContent=String(message);n.classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>n.classList.add('hidden'),4400);}
function messageError(err){notify(err&&err.message?err.message:String(err));}
function tokenClaims(token){const p=token.split('.')[1];if(!p)throw Error('Identity token is incomplete.');return JSON.parse(atob(p.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-p.length%4)%4)));}
function verifyIdentity(token,nonce){const c=tokenClaims(token);if(c.iss!==CONFIG.issuer||c.aud!==CONFIG.client||c.token_use!=='id'||!c.exp||c.exp*1000<=Date.now())throw Error('Identity did not match the Kyro workspace.');if(nonce!==undefined&&c.nonce!==nonce)throw Error('Sign-in verification failed.');return c;}
async function call(url,opts={},timeout=60000){
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeout);
 try{return await fetch(url,{...opts,signal:controller.signal,cache:'no-store'});}
 catch(e){if(e.name==='AbortError')throw Error('The request timed out. The server might still process it.');if(url.startsWith(CONFIG.auth))throw Error('Cannot connect to AWS Cognito sign-in. The Kyro API is reachable, but the identity-provider request was blocked or failed. Reload and sign in again.');throw Error('Unable to connect to the Kyro API. Check the API status and your network.');}
 finally{clearTimeout(timer);}
}
function setSignedOut(message){
 S.token=null;S.refresh=null;S.expires=0;S.account=null;S.current=null;S.conversations=[];S.messages=[];S.pendingUser=null;S.busy=false;
 $('authOverlay').classList.remove('hidden');
 $('authError').textContent=message||'';$('authError').classList.toggle('hidden',!message);
 $('accountName').textContent='Private workspace';$('accountState').textContent='Sign in required';
 $('accountMenu').classList.add('hidden');renderConversations();renderChat();refreshSend();
}
function setSignedIn(claims){
 S.account=claims.email||claims.preferred_username||claims.sub||'Member';
 $('accountName').textContent=S.account;$('accountAvatar').textContent=String(S.account).slice(0,1).toUpperCase();
 $('accountState').textContent='Authenticated';
 $('authOverlay').classList.add('hidden');refreshSend();
}
async function beginLogin(){
 $('authError').classList.add('hidden');$('authSignIn').disabled=true;
 try{
  const verifier=b64url(crypto.getRandomValues(new Uint8Array(32)));
  const challenge=b64url(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier)));
  const state=b64url(crypto.getRandomValues(new Uint8Array(24))),nonce=b64url(crypto.getRandomValues(new Uint8Array(24)));
  sessionStorage.setItem('kyro-temp-chat-pkce',JSON.stringify({verifier,state,nonce,created:Date.now()}));
  const query=new URLSearchParams({response_type:'code',client_id:CONFIG.client,redirect_uri:CONFIG.callback,scope:'openid email profile',code_challenge_method:'S256',code_challenge:challenge,state,nonce});
  location.assign(CONFIG.auth+'/oauth2/authorize?'+query.toString());
 }catch(err){$('authError').textContent=err.message;$('authError').classList.remove('hidden');$('authSignIn').disabled=false;}
}
async function completeLogin(){
 const q=new URLSearchParams(location.search),code=q.get('code'),error=q.get('error');
 if(!code&&!error)return false;
 history.replaceState({},'',location.pathname);
 if(error)throw Error('Cognito sign-in could not finish: '+error+(q.get('error_description')?' — '+q.get('error_description'):'')+'.');
 const raw=sessionStorage.getItem('kyro-temp-chat-pkce');sessionStorage.removeItem('kyro-temp-chat-pkce');
 if(!raw)throw Error('Sign-in session was not found. Start a new sign-in.');
 const saved=JSON.parse(raw);
 if(q.get('state')!==saved.state||Date.now()-saved.created>600000)throw Error('Sign-in state expired or did not match.');
 const data=new URLSearchParams({grant_type:'authorization_code',client_id:CONFIG.client,code,redirect_uri:CONFIG.callback,code_verifier:saved.verifier});
 const res=await call(CONFIG.auth+'/oauth2/token',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:data},20000);
 if(!res.ok){const d=await res.json().catch(()=>({}));throw Error('Cognito rejected the sign-in code (HTTP '+res.status+'): '+String(d.error||'unspecified_error')+'. Please start a NEW sign-in; old authorization codes can only be used once.');}
 const t=await res.json();if(!t.id_token)throw Error('No identity token was returned.');
 const claims=verifyIdentity(t.id_token,saved.nonce);
 S.token=t.id_token;S.refresh=t.refresh_token||null;S.expires=claims.exp*1000;setSignedIn(claims);return true;
}
async function renew(){
 if(!S.refresh)throw Error('Session expired. Please sign in again.');
 const body=new URLSearchParams({grant_type:'refresh_token',client_id:CONFIG.client,refresh_token:S.refresh});
 const res=await call(CONFIG.auth+'/oauth2/token',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body},20000);
 if(!res.ok)throw Error('Unable to renew your Kyro session.');
 const t=await res.json();if(!t.id_token)throw Error('Renewed identity token was not returned.');
 const claims=verifyIdentity(t.id_token);
 S.token=t.id_token;S.expires=claims.exp*1000;if(t.refresh_token)S.refresh=t.refresh_token;
 setSignedIn(claims);
}
async function api(path,method='GET',payload=null){
 if(!S.token)throw Error('Sign in to use Kyro.');
 if(Date.now()+60000>=S.expires)try{await renew();}catch(e){setSignedOut(e.message);throw e;}
 const response=await call(CONFIG.api+'/api/v3'+path,{method,headers:{Authorization:'Bearer '+S.token,...(payload===null?{}:{'Content-Type':'application/json'})},...(payload===null?{}:{body:JSON.stringify(payload)})});
 if(response.status===401){setSignedOut('Kyro API returned HTTP 401: your Cognito session token was not accepted. Sign in again.');throw Error('Kyro API authorization failed (HTTP 401).');}
 const data=await response.json().catch(()=>({error:'Unexpected server response.'}));
 if(!response.ok)throw Error(data.error||data.message||'Kyro API error '+response.status);
 return data;
}
async function health(){
 const dot=$('healthDot'),name=$('healthLabel');
 try{const res=await call(CONFIG.api+'/api/v3/health',{},9500);dot.className='status-dot '+(res.ok?'online':'offline');name.textContent=res.ok?'Kyro API connected':'Kyro API unavailable';}
 catch{dot.className='status-dot offline';name.textContent='Kyro API unreachable';}
}
async function loadConversations(){
 const d=await api('/conversations');S.conversations=Array.isArray(d.conversations)?d.conversations:[];
 renderConversations();
}
function renderConversations(){
 const host=$('conversationList');host.replaceChildren();
 const q=$('searchInput').value.trim().toLowerCase();
 const list=S.conversations.filter(c=>(c.title||'New conversation').toLowerCase().includes(q));
 if(!list.length){host.append(el('p','sidebar-empty',!S.token?'Sign in to load your conversations.':q?'No matching conversations.':'No conversations yet.'));return;}
 for(const c of list){
  const b=el('button','conv-item'+(S.current===c.id?' active':''),c.title||'New conversation');b.type='button';b.title=c.title||'New conversation';
  b.onclick=()=>openConversation(c.id).catch(messageError);host.append(b);
 }
}
function startNewChat(){
 if(S.busy){notify('A reply is still processing.');return;}
 S.current=null;S.messages=[];S.pendingUser=null;renderConversations();renderChat();closeMobile();
 $('messageInput').focus();
}
async function openConversation(id){
 if(S.busy){notify('A reply is still processing.');return;}
 S.current=id;S.messages=[];S.pendingUser=null;renderConversations();renderChat();closeMobile();
 try{await loadMessages(id);}catch(err){messageError(err);}
}
async function loadMessages(id){
 const d=await api('/conversations/'+encodeURIComponent(id)+'/messages');
 if(S.current!==id)return;
 S.messages=Array.isArray(d.messages)?d.messages:[];renderChat();
}
function addSimpleFormatting(host,text){
 const tick=String.fromCharCode(96).repeat(3),parts=String(text||'').split(tick);
 for(let i=0;i<parts.length;i++){
  const block=parts[i];
  if(i%2===1){const pre=el('pre'),code=el('code');const newline=block.indexOf('\n');code.textContent=newline<0?block:block.slice(newline+1);pre.append(code);host.append(pre);}
  else{for(const para of block.split(/\n{2,}/)){if(!para)continue;host.append(el('p',null,para));}}
 }
}
function renderMessage(msg){
 const role=(msg.role||'assistant').toLowerCase();
 const item=el('article','message '+(role==='user'?'user':'assistant'));
 if(role==='user'){item.append(el('div','user-bubble',msg.content||''));return item;}
 item.append(el('div','ai-avatar','✳'));
 const body=el('div','ai-body');body.append(el('div','ai-label','Genesis · research reference'));
 const response=el('div','answer-content');addSimpleFormatting(response,msg.content||'');body.append(response);
 if(msg.content){
  const actions=el('div','message-actions'),copy=el('button','subtle-action','Copy');copy.type='button';copy.setAttribute('aria-label','Copy reply');
  copy.onclick=async()=>{try{await navigator.clipboard.writeText(msg.content);notify('Reply copied.');}catch{notify('Copy is unavailable in this browser.');}};
  actions.append(copy);body.append(actions);
 }
 item.append(body);return item;
}
function renderChat(){
 const empty=$('emptyState'),feed=$('chatFeed');
 const has=Boolean(S.current)||S.messages.length>0||Boolean(S.pendingUser);
 empty.classList.toggle('hidden',has);feed.classList.toggle('hidden',!has);feed.replaceChildren();
 if(!has)return;
 for(const msg of S.messages)feed.append(renderMessage(msg));
 if(S.pendingUser)feed.append(renderMessage({role:'user',content:S.pendingUser}));
 if(S.busy){const loader=el('article','message assistant');loader.append(el('div','ai-avatar','✳'));const body=el('div','ai-body');body.append(el('div','ai-label','Genesis is processing…'));const dots=el('div','typing');for(let i=0;i<3;i++)dots.append(el('i'));body.append(dots);loader.append(body);feed.append(loader);}
 requestAnimationFrame(()=>{$('chatMain').scrollTop=$('chatMain').scrollHeight;});
}
function refreshSend(){$('sendButton').disabled=!S.token||S.busy||!$('messageInput').value.trim();$('messageInput').disabled=S.busy;$('sendButton').textContent=S.busy?'…':'↑';}
function resizeComposer(){const input=$('messageInput');input.style.height='auto';input.style.height=Math.min(165,Math.max(30,input.scrollHeight))+'px';refreshSend();}
async function sendMessage(){
 const content=$('messageInput').value.trim();if(!content||S.busy)return;
 if(!S.token){setSignedOut('Sign in to send messages.');return;}
 S.busy=true;S.pendingUser=content;refreshSend();renderChat();
 try{
  if(!S.current){
   const title=content.replace(/\s+/g,' ').slice(0,68)||'New conversation';
   const created=await api('/conversations','POST',{title});
   if(!created.id)throw Error('Kyro did not return a conversation ID.');
   S.current=created.id;S.conversations.unshift({id:created.id,title});
   renderConversations();
  }
  const id=S.current;
  await api('/conversations/'+encodeURIComponent(id)+'/generate','POST',{content,request_id:crypto.randomUUID()});
  S.pendingUser=null;S.busy=false;
  $('messageInput').value='';resizeComposer();
  await loadMessages(id);await loadConversations();
 }catch(err){S.pendingUser=null;S.busy=false;renderChat();messageError(err);}
 finally{refreshSend();}
}
function exportCurrent(){
 if(!S.current){notify('Open a conversation before exporting.');return;}
 const conv=S.conversations.find(x=>x.id===S.current),title=(conv&&conv.title)||'Kyro conversation';
 const payload={title,conversation_id:S.current,exported_at:new Date().toISOString(),messages:S.messages.map(m=>({role:m.role,content:m.content,created_at:m.created_at||null}))};
 const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
 a.href=url;a.download='kyro-chat-'+new Date().toISOString().slice(0,10)+'.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 notify('Conversation exported to JSON.');
}
function toggleSidebar(){
 if(innerWidth<=700){const open=!$('sidebar').classList.contains('mobile-open');$('sidebar').classList.toggle('mobile-open',open);$('mobileScrim').classList.toggle('hidden',!open);}
 else{$('sidebar').classList.toggle('collapsed');S.sidebarOpen=!$('sidebar').classList.contains('collapsed');}
}
function closeMobile(){$('sidebar').classList.remove('mobile-open');$('mobileScrim').classList.add('hidden');}
function applyTheme(){document.body.classList.toggle('dark',localStorage.getItem('kyro-temp-theme')==='dark');}
function toggleTheme(){localStorage.setItem('kyro-temp-theme',document.body.classList.contains('dark')?'light':'dark');applyTheme();$('accountMenu').classList.add('hidden');}
function logout(){
 S.token=null;S.refresh=null;S.expires=0;sessionStorage.removeItem('kyro-temp-chat-pkce');
 location.assign(CONFIG.auth+'/logout?'+new URLSearchParams({client_id:CONFIG.client,logout_uri:CONFIG.callback}));
}
function dictate(){
 const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!Speech){notify('Dictation is not supported by this browser.');return;}
 if(S.speech){S.speech.stop();return;}
 const rec=new Speech();rec.lang=navigator.language||'en-NZ';rec.interimResults=false;rec.continuous=false;
 S.speech=rec;$('dictateButton').textContent='■';
 rec.onresult=e=>{const t=e.results[0][0].transcript;$('messageInput').value+=($('messageInput').value?' ':'')+t;resizeComposer();};
 rec.onerror=e=>notify('Dictation: '+(e.error||'microphone error'));
 rec.onend=()=>{S.speech=null;$('dictateButton').textContent='♩';};
 try{rec.start();}catch{rec.onend();notify('Microphone could not start.');}
}
async function runDiagnostics(){
 const b=$('runDiagnostics'),host=$('diagnosticResults'),copy=$('copyDiagnostics');
 b.disabled=true;b.textContent='Checking connections…';host.classList.remove('hidden');host.textContent='Running safe checks. No credentials or authorization codes are included.';
 const lines=['KYRO CHAT DIAGNOSTIC v2','UTC: '+new Date().toISOString(),'Site: '+location.origin,'Secure page: '+String(location.protocol==='https:')];
 try{
  if(!window.crypto||!crypto.subtle)lines.push('PKCE support: NOT AVAILABLE');else lines.push('PKCE support: OK');
  const test='kyro-temp-diag-'+Date.now();sessionStorage.setItem(test,'ok');
  lines.push('Tab session storage: '+(sessionStorage.getItem(test)==='ok'?'OK':'FAILED'));sessionStorage.removeItem(test);
 }catch{lines.push('Browser storage: BLOCKED');}
 const check=async(label,url,options,expected)=>{
  const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),11000);
  try{
   const r=await fetch(url,{...options,cache:'no-store',signal:ctl.signal});
   const success=expected(r.status);
   lines.push(label+': '+(success?'REACHABLE':'UNEXPECTED')+' (HTTP '+r.status+')');
   return success;
  }catch(e){
   lines.push(label+': FAILED ('+(e?.name==='AbortError'?'timeout':'blocked / network / CORS')+')');
   return false;
  }finally{clearTimeout(timer);}
 };
 await check('Kyro public API',CONFIG.api+'/api/v3/health',{method:'GET'},s=>s===200);
 await check('Kyro protected API (401 expected)',CONFIG.api+'/api/v3/conversations',{method:'GET'},s=>s===401);
 await check('Cognito token endpoint (400 expected)',CONFIG.auth+'/oauth2/token',{
  method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
  body:new URLSearchParams({grant_type:'refresh_token',client_id:CONFIG.client,refresh_token:'diagnostic-invalid-token'})
 },s=>s===400);
 lines.push('NOTE: These checks DO NOT attempt login or send any password.');
 lines.push('If all endpoints are reachable but login fails, share the exact on-screen sign-in error.');
 const report=lines.join('\n');host.textContent=report;copy.classList.remove('hidden');
 copy.onclick=async()=>{try{await navigator.clipboard.writeText(report);notify('Diagnostic report copied.');}catch{notify('Copy blocked; select the report text instead.');}};
 b.disabled=false;b.textContent='Run connection checks again';
}
function bindEvents(){
 $('authSignIn').onclick=beginLogin;$('runDiagnostics').onclick=runDiagnostics;$('newChat').onclick=startNewChat;$('newChatTop').onclick=startNewChat;
 $('sidebarToggle').onclick=toggleSidebar;$('closeSidebar').onclick=closeMobile;$('mobileScrim').onclick=closeMobile;
 $('searchToggle').onclick=()=>{$('searchInput').classList.toggle('hidden');$('searchInput').focus();};
 $('searchInput').oninput=renderConversations;$('checkHealth').onclick=health;
 $('sendButton').onclick=sendMessage;$('messageInput').oninput=resizeComposer;
 $('messageInput').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();sendMessage();}};
 $('exportButton').onclick=exportCurrent;$('dictateButton').onclick=dictate;
 $('modelInfo').onclick=()=>notify('Genesis is currently an experimental research reference, not a verified neural model deployment.');
 $('accountButton').onclick=()=>{$('accountMenu').classList.toggle('hidden');};
 $('signOutButton').onclick=logout;$('themeButton').onclick=toggleTheme;
 document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>{$('messageInput').value=b.dataset.prompt;resizeComposer();$('messageInput').focus();});
 document.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('searchInput').classList.remove('hidden');$('searchInput').focus();}
  if((e.ctrlKey||e.metaKey)&&e.shiftKey&&e.key.toLowerCase()==='o'){e.preventDefault();startNewChat();}
  if(e.key==='Escape'){closeMobile();$('accountMenu').classList.add('hidden');$('searchInput').blur();}
 });
}
async function init(){
 applyTheme();bindEvents();refreshSend();renderChat();renderConversations();
 health().catch(()=>{});setInterval(()=>health().catch(()=>{}),90000);
 let authenticated=false;
 try{authenticated=await completeLogin();}
 catch(err){setSignedOut(err.message);return;}
 if(authenticated){
  try{await loadConversations();startNewChat();}
  catch(err){
   if(S.token){notify('Sign-in succeeded, but conversations could not load: '+err.message);renderConversations();}
  }
 }
}
document.addEventListener('DOMContentLoaded',init);