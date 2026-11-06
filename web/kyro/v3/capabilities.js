/* Kyro seven capabilities: attached only to existing authenticated workspace. */
(function () {
'use strict';
const byId = id => document.getElementById(id);
const service = (path,method='GET',body=null) => api('/capabilities'+path,method,body);
function node(type,text,className) {
  const el=document.createElement(type);
  if(text!==undefined&&text!==null)el.textContent=String(text);
  if(className)el.className=className;
  return el;
}
function add(parent,type,text,cls){const e=node(type,text,cls);parent.appendChild(e);return e;}
async function guard(fn) {
  try {byId('cap-error').textContent='';await fn();}
  catch (err) {byId('cap-error').textContent=err.message||String(err);}
}
function button(parent,text,fn) {
  const b=add(parent,'button',text,'secondary small cap-button');
  b.type='button';b.onclick=()=>guard(fn);return b;
}
function section(parent,title) {
  const item=add(parent,'section',null,'cap-feature');
  add(item,'h3',title);return item;
}
function card(parent,title,detail) {
  const item=add(parent,'div',null,'cap-item');
  add(item,'strong',title);
  if(detail)add(item,'p',detail,'cap-muted');
  return item;
}
function ask(text,defaultValue='') {
  const value=prompt(text,defaultValue);
  return value===null?null:value.trim();
}
function askRequired(text,defaultValue='') {
  const value=ask(text,defaultValue);
  return value===null?null:value||null;
}
function requireConfirmation(message) {return confirm(message);}
async function load() {
  const root=byId('capabilities-root');if(!root)return;
  root.replaceChildren();
  const top=add(root,'div',null,'cap-heading');
  add(top,'h2','Seven capabilities. Your controls.');
  add(top,'p','Invite-only beta. Records are scoped to your signed-in account. No autonomous engine execution, and reviews are not independent verification.','cap-muted');
  add(top,'p','','cap-error').id='cap-error';
  const grid=add(root,'div',null,'cap-grid');
  const privacy=section(grid,'7 · Privacy & consent');
  add(privacy,'p','All new feature records start disabled. Revoking consent deletes records within this beta service only, not historic chat or backups.','cap-muted');
  const status=await service('/status');
  const labels={tasks:'Task tracking',memory:'Explicit long-term memory',personalization:'Preferences',proactive:'Proactive attention',provenance:'Claim/source records'};
  for(const scope of Object.keys(labels)) {
    const label=add(privacy,'label',null,'cap-consent');
    const check=add(label,'input');check.type='checkbox';check.checked=!!status.consents[scope];
    add(label,'span',labels[scope]);
    check.onchange=()=>guard(async()=>{
      if(!check.checked && !requireConfirmation('Disable '+labels[scope]+' and delete its new beta records?')){check.checked=true;return;}
      await service('/consents','POST',{scope,enabled:check.checked});await load();
    });
  }
  const privacyActions=add(privacy,'div',null,'cap-actions');
  button(privacyActions,'Export my beta data',async()=>{
    const data=await service('/export');
    const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download='kyro-beta-capabilities.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),300);
  });
  button(privacyActions,'Erase my beta records',async()=>{
    if(ask('Type ERASE_MY_BETA_DATA to confirm:')!=='ERASE_MY_BETA_DATA')return;
    await service('/erase','POST',{confirm:'ERASE_MY_BETA_DATA'});await load();
  });

  const tasks=section(grid,'1 · Finish & review tasks');
  add(tasks,'p','Define outcomes, attach evidence and explicitly attest completion. Genesis cannot claim execution just by describing it.','cap-muted');
  button(tasks,'Create task',async()=>{
    const title=askRequired('Task title');if(!title)return;
    const raw=askRequired('Acceptance criteria (one per line)');if(!raw)return;
    const criteria=raw.split('\n').map(x=>x.trim()).filter(Boolean);
    await service('/tasks','POST',{title,criteria});await load();
  });
  if(status.consents.tasks){
    const data=await service('/tasks');
    for(const t of data.tasks){
      const item=card(tasks,t.title+' · '+t.status.replaceAll('_',' '),'Success conditions: '+t.criteria.join(' | '));
      const actions=add(item,'div',null,'cap-actions');
      const transitions={DRAFT:['approve','cancel'],APPROVED:['start','block','cancel'],WORKING:['review','block','cancel'],REVIEW:['revise','block','cancel'],BLOCKED:['start','cancel']};
      for(const action of transitions[t.status]||[])button(actions,action,async()=>{
        await service('/tasks/transition','POST',{id:t.id,action});await load();
      });
      if(t.status==='WORKING')button(actions,'Add evidence',async()=>{
        const i=ask('Which criterion number?', '1');if(i===null)return;
        const observation=askRequired('What happened? Evidence is not independently verified.');if(!observation)return;
        const reference=askRequired('Reference or test output location');if(!reference)return;
        await service('/tasks/evidence','POST',{id:t.id,criterion_index:Number(i)-1,observation,reference});await load();
      });
      for(const e of t.evidence||[]){
        const ev=card(item,'Evidence '+(e.criterion_index+1)+' — '+e.review_state,e.observation+' | Reference: '+e.reference);
        if(t.status==='REVIEW'&&e.review_state==='PENDING'){
          button(ev,'Accept',async()=>{await service('/tasks/review','POST',{id:t.id,evidence_id:e.id,accepted:true});await load();});
          button(ev,'Reject',async()=>{await service('/tasks/review','POST',{id:t.id,evidence_id:e.id,accepted:false});await load();});
        }
      }
      if(t.status==='REVIEW')button(actions,'Attest completion',async()=>{
        if(!confirm('I have examined accepted evidence for each criterion and attest the task is complete. This is not independent verification.'))return;
        await service('/tasks/complete','POST',{id:t.id,human_confirmed:true});await load();
      });
    }
  } else add(tasks,'p','Enable task tracking above to start.','cap-muted');

  const attention=section(grid,'2 · Proactive assistance');
  add(attention,'p','Opt-in due reminders. Nothing runs or sends notifications in the background.','cap-muted');
  button(attention,'Add follow-up',async()=>{
    const title=askRequired('What should Kyro remind you about?');if(!title)return;
    const date=askRequired('Due date and time with timezone, e.g. 2026-11-08T10:00:00+13:00');
    if(!date)return;
    await service('/nudges','POST',{title,due_at:date});await load();
  });
  if(status.consents.proactive){
    const d=await service('/attention');
    for(const n of d.nudges){
      const it=card(attention,n.title,'Due: '+new Date(n.due_at).toLocaleString());
      button(it,'Dismiss',async()=>{await service('/nudges/dismiss','POST',{id:n.id});await load();});
    }
    for(const t of d.tasks)card(attention,'Task needs review: '+t.title,t.status);
    if(!d.nudges.length&&!d.tasks.length)add(attention,'p','Nothing due now.','cap-muted');
  } else add(attention,'p','Enable proactive attention above.','cap-muted');

  for(const [kind,title,scope] of [['preference','3 · Personal preferences','personalization'],['memory','5 · Context memory','memory']]){
    const p=section(grid,title);
    add(p,'p','Only information you explicitly choose to save.','cap-muted');
    button(p,'Save '+kind,async()=>{
      const key=askRequired('Name of '+kind);if(!key)return;
      const value=askRequired('Value to remember');if(!value)return;
      await service('/memory','POST',{kind,key,value});await load();
    });
    if(status.consents[scope]){
      const r=await api('/capabilities/memory?kind='+encodeURIComponent(kind));
      for(const item of r.items){
        const row=card(p,item.key,item.value);
        button(row,'Forget',async()=>{
          if(!confirm('Forget this '+kind+' from the beta store?'))return;
          await service('/memory/forget','POST',{kind,key:item.key});await load();
        });
      }
    }else add(p,'p','Permission disabled.','cap-muted');
  }
  const claims=section(grid,'4 · Evidence & accuracy');
  add(claims,'p','Store sources and mark your own review. A listed URL is not independent proof.','cap-muted');
  button(claims,'Record claim',async()=>{
    const statement=askRequired('Claim to investigate');if(!statement)return;
    const raw=ask('Source references, one per line; leave empty if unknown')||'';
    await service('/claims','POST',{statement,sources:raw.split('\n').map(x=>x.trim()).filter(Boolean)});await load();
  });
  if(status.consents.provenance){
    const out=await service('/claims');
    for(const c of out.claims){
      const row=card(claims,c.statement,'Status: '+c.status+' | Independently verified: no | '+c.sources.join(' | '));
      if(c.status==='UNSUPPORTED'||c.status==='SOURCES_LISTED_UNCHECKED'){
        button(row,'My review: supported',async()=>{await service('/claims/review','POST',{id:c.id,supported:true});await load();});
        button(row,'My review: disputed',async()=>{await service('/claims/review','POST',{id:c.id,supported:false});await load();});
      }
    }
  }else add(claims,'p','Permission disabled.','cap-muted');

  const decisions=section(grid,'6 · Decision support');
  add(decisions,'p','Compare two options with transparent, user-supplied 0–5 scores and weighted priorities.','cap-muted');
  const answer=add(decisions,'div',null,'cap-decisions');
  button(decisions,'Compare two options',async()=>{
    const c1=askRequired('First criterion','Quality');if(!c1)return;
    const c2=askRequired('Second criterion','Cost');if(!c2)return;
    const w1=askRequired('Weight for '+c1,'3');if(w1===null)return;
    const w2=askRequired('Weight for '+c2,'1');if(w2===null)return;
    const a=askRequired('First option','Option A');if(!a)return;
    const b=askRequired('Second option','Option B');if(!b)return;
    const a1=askRequired(a+' / '+c1+' rating 0–5','4');if(a1===null)return;
    const a2=askRequired(a+' / '+c2+' rating 0–5','2');if(a2===null)return;
    const b1=askRequired(b+' / '+c1+' rating 0–5','3');if(b1===null)return;
    const b2=askRequired(b+' / '+c2+' rating 0–5','5');if(b2===null)return;
    const r=await service('/decisions/compare','POST',{
      criteria:[{name:c1,weight:Number(w1)},{name:c2,weight:Number(w2)}],
      options:[{name:a,scores:{[c1]:Number(a1),[c2]:Number(a2)}},
               {name:b,scores:{[c1]:Number(b1),[c2]:Number(b2)}}]});
    answer.replaceChildren();
    for(const x of r.ranking)card(answer,x.name+' — '+x.score_out_of_5.toFixed(2)+'/5',
      Object.entries(x.contributions).map(([k,v])=>k+': '+v.toFixed(2)).join(' · '));
    add(answer,'p',r.caveat,'cap-muted');
  });
}
window.kyroCapabilityLoad=()=>guard(load);
})();