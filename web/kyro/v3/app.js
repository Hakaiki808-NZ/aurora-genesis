'use strict';
// Browser PKCE. Tokens stay in RAM, never localStorage or shared cookies.
// Reloading the tab intentionally requires a fresh authenticated Cognito redirect.
const CONFIG=Object.freeze({api:'https://ces52hcf3e.execute-api.ap-southeast-2.amazonaws.com',client:'68i1h2nqhvsjruneo12k0u3ahm',auth:'https://kyro-v4-private-179502447662.auth.ap-southeast-2.amazoncognito.com',callback:'https://d3j65cc3p66kzr.cloudfront.net/v3/index.html'});
const state={token:null,refreshToken:null,expiresAt:0,project:null,projects:[],file:null,etag:null,conversation:null,mode:'profile'};
const $=id=>document.getElementById(id);
const node=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=String(txt);if(cls)e.className=cls;return e;};
const b64url=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
function notice(msg){
 $('notice').textContent=msg;
 if(!$('signin').classList.contains('hidden')){
  $('signin-error').textContent=msg;
  $('signin-error').classList.remove('hidden');
 }
}
function clearSigninError(){ $('signin-error').textContent='';$('signin-error').classList.add('hidden'); }
function showSignedOut(message='Sign in to continue.'){
 state.token=null;state.refreshToken=null;state.expiresAt=0;
 state.project=null;state.projects=[];state.file=null;state.etag=null;state.conversation=null;
 $('project-list').replaceChildren();$('file-list').replaceChildren();$('messages').replaceChildren();
 $('workspace').classList.add('hidden');$('signin').classList.remove('hidden');
 $('account-name').textContent='Sign in';
 notice(message);
}
function decodeJwt(token){
 const payload=token.split('.')[1];
 if(!payload)throw new Error('Malformed identity token.');
 const encoded=payload.replace(/-/g,'+').replace(/_/g,'/');
 const normalized=encoded+'='.repeat((4-encoded.length%4)%4);
 return JSON.parse(atob(normalized));
}
function checkIdentity(token,nonce=null){
 const payload=decodeJwt(token);
 const expectedIssuer='https://cognito-idp.ap-southeast-2.amazonaws.com/ap-southeast-2_Pq71kumUV';
 if(payload.iss!==expectedIssuer || payload.aud!==CONFIG.client || payload.token_use!=='id' || payload.exp*1000<=Date.now())
  throw new Error('Identity token did not match this workspace.');
 if(nonce!==null && payload.nonce!==nonce)throw new Error('Sign-in session verification failed.');
 return payload;
}
async function renewSession(){
 if(!state.refreshToken)throw new Error('Your session has expired. Please sign in again.');
 const body=new URLSearchParams({grant_type:'refresh_token',client_id:CONFIG.client,refresh_token:state.refreshToken});
 const res=await fetch(CONFIG.auth+'/oauth2/token',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body});
 if(!res.ok)throw new Error('Your session could not be renewed. Sign in again.');
 const result=await res.json();
 if(!result.id_token)throw new Error('Cognito did not issue a renewed identity token.');
 const claims=checkIdentity(result.id_token);
 state.token=result.id_token;state.expiresAt=claims.exp*1000;
 if(result.refresh_token)state.refreshToken=result.refresh_token;
}
async function request(url,options={},timeout=35000){
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),timeout);
 try{return await fetch(url,{...options,signal:controller.signal});}
 catch(e){if(e.name==='AbortError')throw new Error('Kyro request timed out. Try again.');throw new Error('Network connection unavailable. Check connectivity and retry.');}
 finally{clearTimeout(timer);}
}
async function beginLogin(){
 clearSigninError();
 const verifier=b64url(crypto.getRandomValues(new Uint8Array(32)));
 const challenge=b64url(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier)));
 const stateKey=b64url(crypto.getRandomValues(new Uint8Array(24)));
 const nonce=b64url(crypto.getRandomValues(new Uint8Array(24)));
 sessionStorage.setItem('kyro-v3-pkce',JSON.stringify({verifier,stateKey,nonce,created:Date.now()}));
 const q=new URLSearchParams({response_type:'code',client_id:CONFIG.client,redirect_uri:CONFIG.callback,scope:'openid email profile',code_challenge_method:'S256',code_challenge:challenge,state:stateKey,nonce});
 location.assign(CONFIG.auth+'/oauth2/authorize?'+q.toString());
}
async function finishLogin(){
 const params=new URLSearchParams(location.search);
 const code=params.get('code');const error=params.get('error');
 if(error){history.replaceState({},'',location.pathname);throw new Error('Login was not completed: '+error+'. Check your account invitation and try again.');}
 if(!code)return false;
 const saved=sessionStorage.getItem('kyro-v3-pkce');
 sessionStorage.removeItem('kyro-v3-pkce');
 history.replaceState({},'',location.pathname);
 if(!saved)throw new Error('Login session missing. Start again.');
 const data=JSON.parse(saved);
 if(data.stateKey!==params.get('state')||Date.now()-data.created>600000)throw new Error('Login state invalid or expired.');
 const body=new URLSearchParams({grant_type:'authorization_code',client_id:CONFIG.client,code,redirect_uri:CONFIG.callback,code_verifier:data.verifier});
 const response=await request(CONFIG.auth+'/oauth2/token',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body});
 if(!response.ok)throw new Error('Cognito token exchange failed ('+response.status+').');
 const result=await response.json();
 if(!result.id_token)throw new Error('No identity token returned.');
 const payload=checkIdentity(result.id_token,data.nonce);
 state.token=result.id_token;state.refreshToken=result.refresh_token||null;state.expiresAt=payload.exp*1000;clearSigninError();notice('Signed in. Loading your private workspace…');return true;
}
async function api(path,method='GET',body=null){
 if(!state.token)throw new Error('Sign in required');
 if(state.expiresAt && Date.now()+60000>=state.expiresAt){
  try{await renewSession();}catch(e){showSignedOut(e.message);throw e;}
 }
 const opts={method,headers:{Authorization:'Bearer '+state.token,...(body!==null?{'content-type':'application/json'}:{})},...(body!==null?{body:JSON.stringify(body)}:{})};
 let res=await request(CONFIG.api+'/api/v3'+path,opts,45000);
 if(res.status===401){
  // A failed JWT must never be retried with the same credentials.
  showSignedOut('Your login is no longer valid. Sign in again.');
  throw new Error('Session expired. Sign in again.');
 }
 const data=await res.json().catch(()=>({error:'Unexpected non-JSON API response'}));
 if(!res.ok)throw new Error(data.error||'API '+res.status);
 return data;
}
const safe=async fn=>{try{return await fn();}catch(e){notice(e.message||String(e));return null;}};
function show(mode){state.mode=mode;for(const el of document.querySelectorAll('[data-mode]'))el.classList.toggle('active',el.dataset.mode===mode);
 for(const name of ['profile','overview','code','collab','chat','connectors','school','capabilities'])$(name+'-panel').classList.toggle('hidden',name!==mode);
 const info={profile:['PROFILE','YOUR ACCOUNT','Your personal Kyro space.','Manage your profile, projects and launch the app.'],overview:['OVERVIEW','YOUR WORKSPACE','Welcome to Kyro.','Everything in one focused workspace.'],code:['CODE','CODE WORKSPACE','Build with intelligence.','Versioned source files. Approved and auditable changes.'],collab:['COLLABORATE','SHARED WORKSPACE','Better work, together.','Discuss work and share access by project role.'],chat:['CHAT ARCHIVE','PRIVATE CONVERSATIONS','Keep your thinking.','Conversation history and deterministic Genesis reference responses (experimental).'],connectors:['PLUGINS','CONNECTORS & APIs','Connect with control.','Adapters are registered; integrations are disabled until authorized.'],school:['REALIGNMENT SCHOOL','CONTROLLED LEARNING','Learn from mistakes.','Diagnosis, feedback and safe correction exercises.'],capabilities:['AI CAPABILITIES','SEVEN CAPABILITIES','Practical AI, under your control.','Task outcomes, consent, memory, evidence and clear decisions.']};
 const [name,label,title,blurb]=info[mode];$('mode-title').textContent=name;$('section-label').textContent=label;$('section-title').textContent=title;$('section-blurb').textContent=blurb;
 if(mode==='school' && window.kyroSchoolLoad) safe(()=>window.kyroSchoolLoad());if(mode==='capabilities' && window.kyroCapabilityLoad) safe(()=>window.kyroCapabilityLoad());if(mode==='profile'){$('profile-project-count').textContent=String(state.projects.length);}if(mode==='overview'){const m=$('metric-projects');if(m)m.textContent=String(state.projects.length);const p=state.projects.find(x=>x.id===state.project);const a=$('metric-active');if(a)a.textContent=p?p.name:'None selected';}if(mode==='collab')safe(loadPosts);if(mode==='chat')safe(loadConversations);if(mode==='connectors')safe(loadConnectors);if(mode==='code')safe(loadFiles);
}
async function boot(){
 const entryQuery=new URLSearchParams(location.search);
 if(entryQuery.has('app'))sessionStorage.setItem('kyro-v3-entry-intent','app');
 else if(entryQuery.has('profile'))sessionStorage.setItem('kyro-v3-entry-intent','profile');
 $('login').onclick=()=>safe(beginLogin);
 $('launch-kyro-app').onclick=()=>{window.open('/v3/index.html?app=1','_blank','popup=yes,width=1440,height=900,noopener,noreferrer');};
 document.querySelectorAll('[data-go]').forEach(el=>el.addEventListener('click',()=>{if(state.token)show(el.dataset.go);}));

 $('account-btn').onclick=()=>{if(!state.token){safe(beginLogin);return;}state.token=null;state.refreshToken=null;location.assign(CONFIG.auth+'/logout?'+new URLSearchParams({client_id:CONFIG.client,logout_uri:CONFIG.callback}));};
 document.querySelectorAll('[data-mode]').forEach(el=>el.onclick=()=>show(el.dataset.mode));
 $('new-project').onclick=()=>safe(newProject);$('new-file').onclick=()=>safe(newFile);$('save-file').onclick=()=>safe(saveFile);$('draft-job').onclick=()=>safe(draftJob);
 $('post-form').onsubmit=e=>{e.preventDefault();safe(post)};
 $('invite-viewer').onclick=()=>safe(()=>invite('viewer'));
 $('invite-editor').onclick=()=>safe(()=>invite('editor'));
 $('join-invite').onclick=()=>safe(joinInvite);
 $('new-chat').onclick=()=>safe(newConversation);
 $('chat-form').onsubmit=e=>{e.preventDefault();safe(saveMessage)};
 try{const r=await request(CONFIG.api+'/api/v3/health',{},9000);$('api-status').textContent=r.ok?'Cloud API online':'Cloud API unavailable';}catch{$('api-status').textContent='Cloud API unavailable';}
 const params=new URLSearchParams(location.search);
 if(params.has('app')&&!params.has('code')&&!params.has('error')&&!state.token){await safe(beginLogin);return;}
 if(params.has('code')||params.has('error'))await safe(finishLogin);
 if(state.token){
  $('signin').classList.add('hidden');$('workspace').classList.remove('hidden');
  const me=await safe(()=>api('/me'));
  if(!me){showSignedOut('Could not verify your workspace account. Sign in again.');return;}$('account-name').textContent='Account · '+String(me.subject||'member').slice(0,10);
  const claims=checkIdentity(state.token);
  const displayName=typeof claims.name==='string'&&claims.name.trim()?claims.name.trim():typeof claims.given_name==='string'&&claims.given_name.trim()?claims.given_name.trim():'Kyro member';
  $('profile-name').textContent=displayName.slice(0,80);
  $('profile-email').textContent=claims.email_verified===true&&typeof claims.email==='string'?claims.email:'Verified private-alpha account';
  await safe(loadProjects);
  const intended=sessionStorage.getItem('kyro-v3-entry-intent')==='app'?'overview':'profile';
  sessionStorage.removeItem('kyro-v3-entry-intent');
  show(intended);notice('Private workspace connected.');
 } else if(!params.has('error')&&!params.has('code')){$('signin-error').classList.add('hidden');}
}
async function loadProjects(){
 const data=await api('/projects');state.projects=data.projects||[];
 const host=$('project-list');host.replaceChildren();
 for(const p of state.projects){const btn=node('button',p.name+' · '+p.role,'project'+(state.project===p.id?' active':''));btn.onclick=()=>selectProject(p.id);host.append(btn);}
 if(!state.project&&state.projects.length)await selectProject(state.projects[0].id);
}
async function newProject(){const name=prompt('Name the new project');if(!name||!name.trim())return;
 const data=await api('/projects','POST',{name:name.trim()});notice('Project created.');await loadProjects();await selectProject(data.id);}
async function selectProject(id){state.project=id;state.file=null;state.etag=null;setProjectPermissions();await loadProjectsUI();
 if(state.mode==='code')await safe(loadFiles);if(state.mode==='collab')await safe(loadPosts);await safe(loadJobs);}
function setProjectPermissions(){
 const membership=state.projects.find(p=>p.id===state.project);
 const role=membership?.role||'none';
 const editable=role==='owner'||role==='editor';
 $('new-file').disabled=!editable;
 $('save-file').disabled=!editable||!state.file;
 $('file-content').readOnly=!editable;
 $('draft-job').disabled=!editable;
 $('post-input').disabled=!editable;
 $('post-form').querySelector('button[type=submit]').disabled=!editable;
 $('invite-viewer').disabled=role!=='owner';
 $('invite-editor').disabled=role!=='owner';
 $('file-notice').textContent=editable?'Every save is version checked.':'View-only project; ask an owner for editor access.';
}
function loadProjectsUI(){const hosts=$('project-list').children;for(let i=0;i<hosts.length;i++)hosts[i].classList.toggle('active',state.projects[i]?.id===state.project);}
async function loadFiles(){const host=$('file-list');host.replaceChildren();if(!state.project){host.append(node('p','Create a project to start.'));return;}
 const data=await api('/projects/'+state.project+'/files');
 for(const f of (data.files||[]).filter(f=>f.path.toLowerCase().includes(($('file-filter')?.value||'').trim().toLowerCase()))){const btn=node('button','⌘  '+f.path,'file-entry'+(state.file===f.path?' selected':''));btn.onclick=()=>safe(()=>openFile(f.path));host.append(btn);}
 if(!data.files?.length)host.append(node('p','No source files yet.','pad'));else if(!host.children.length)host.append(node('p','No matching files.','pad'));}
async function newFile(){if(!state.project)throw new Error('Select a project first.');const path=prompt('File path, for example src/main.py');if(!path)return;
 state.file=path;state.etag=null;$('file-name').textContent=path;$('file-content').value='';window.kyroCleanContent='';document.getElementById('dirty-indicator')?.classList.add('hidden');$('save-file').disabled=false;setProjectPermissions();$('file-etag').textContent='New file';notice('Save to create the file.');}
async function openFile(path){const data=await api('/projects/'+state.project+'/file?path='+encodeURIComponent(path));state.file=data.path;state.etag=data.etag;
 $('file-name').textContent=data.path;$('file-content').value=data.content;window.kyroCleanContent=data.content;document.getElementById('dirty-indicator')?.classList.add('hidden');$('file-etag').textContent=data.etag.slice(0,9);$('save-file').disabled=false;setProjectPermissions();await loadFiles();}
async function saveFile(){if(!state.project||!state.file)throw new Error('Select or create a file.');
 if(!['owner','editor'].includes(state.projects.find(p=>p.id===state.project)?.role))throw new Error('Viewer access is read-only.');
 const payload={path:state.file,content:$('file-content').value};if(state.etag)payload.if_match=state.etag;
 const data=await api('/projects/'+state.project+'/files','PUT',payload);state.etag=data.etag;window.kyroCleanContent=$('file-content').value;document.getElementById('dirty-indicator')?.classList.add('hidden');$('file-etag').textContent=data.etag.slice(0,9);notice('File saved with integrity version '+data.etag.slice(0,12));await loadFiles();}
async function draftJob(){if(!state.project)throw new Error('Choose a project.');const data=await api('/projects/'+state.project+'/jobs','POST',{operation:'lint'});notice(data.reason);await loadJobs();}
async function loadJobs(){const host=$('jobs');host.replaceChildren();if(!state.project)return;
 const data=await api('/projects/'+state.project+'/jobs');for(const j of data.jobs||[])host.append(node('div',j.operation+' · '+j.status,'job'));}
async function loadPosts(){const host=$('posts');host.replaceChildren();if(!state.project){host.append(node('p','Choose a project to begin.'));return;}
 const data=await api('/projects/'+state.project+'/posts');for(const p of data.posts||[]){const item=node('div',undefined,'post');item.append(node('strong',p.author),node('div',p.body),node('time',p.created_at));host.append(item);}host.scrollTop=host.scrollHeight;}
async function post(){if(!state.project)throw new Error('Choose a project first.');const input=$('post-input');if(!input.value.trim())return;
 await api('/projects/'+state.project+'/posts','POST',{body:input.value.trim()});input.value='';await loadPosts();}
async function invite(role){if(!state.project)throw new Error('Choose a project.');const res=await api('/projects/'+state.project+'/invites','POST',{role});
 $('invite-output').value=res.invitation_token;notice('One-use '+role+' invitation token issued. Copy it before navigating away.');}
async function joinInvite(){const token=prompt('Paste your one-time invitation token');if(!token)return;const data=await api('/invitations/accept','POST',{token});await loadProjects();await selectProject(data.project_id);show('collab');notice('Joined workspace as '+data.role);}
async function loadConversations(){const host=$('conv-list');host.replaceChildren();const data=await api('/conversations');
 for(const c of data.conversations||[]){const btn=node('button',c.title,'project');btn.onclick=()=>safe(()=>openConversation(c.id));host.append(btn);}
 if(!state.conversation&&data.conversations.length)await openConversation(data.conversations[0].id);}
async function newConversation(){const data=await api('/conversations','POST',{title:'New conversation'});state.conversation=data.id;await loadConversations();await openConversation(data.id);}
async function openConversation(id){state.conversation=id;const host=$('messages');host.replaceChildren();const data=await api('/conversations/'+id+'/messages');
 for(const m of data.messages||[]){const item=node('div',undefined,'post');item.append(node('strong',m.role),node('div',m.content));host.append(item);}host.scrollTop=host.scrollHeight;}
async function saveMessage(){if(!state.conversation)throw new Error('Create a conversation first.');const input=$('chat-input');if(!input.value.trim())return;
 const button=$('chat-form').querySelector('button[type=submit]');if(button)button.disabled=true;try{const result=await api('/conversations/'+state.conversation+'/generate','POST',{content:input.value.trim(),request_id:crypto.randomUUID()});input.value='';await openConversation(state.conversation);window.kyroVoiceAfterReply?.();notice('Response from '+result.model+' (experimental research reference).');}finally{if(button)button.disabled=false;}}
async function loadConnectors(){const data=await api('/connectors');const host=$('connectors-list');host.replaceChildren();
 for(const c of data.connectors||[]){const item=node('div',undefined,'connector');item.append(node('strong',c.id),node('small',c.protocol),node('div',c.scope),node('div',c.state,'status'));host.append(item);}}
document.addEventListener('DOMContentLoaded',()=>{boot().catch(e=>notice(e.message||String(e)));});