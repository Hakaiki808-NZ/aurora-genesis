('use strict');
document.addEventListener('DOMContentLoaded',()=>{
  const byId=id=>document.getElementById(id);
  const overlay=byId('command-overlay'),input=byId('command-input'),results=byId('command-results');
  const prefs=byId('prefs-overlay');
  const modes=[['overview','Overview','Workspace dashboard'],['code','Code','Project files and editor'],['collab','Collaborate','Project messages and sharing'],['chat','Chat archive','Genesis research conversations'],['connectors','Plugins & integrations','Connected tool contracts']];
  let lastFocus=null;
  function setOpen(el,on){if(!el)return;el.classList.toggle('hidden',!on);document.body.classList.toggle('dialog-open',on);if(!on&&lastFocus?.focus)lastFocus.focus();}
  function go(mode){const el=document.querySelector('[data-mode="'+mode+'"]');if(el){el.click();setOpen(overlay,false);setOpen(prefs,false);}}
  function paint(){
    const q=(input?.value||'').trim().toLowerCase();if(!results)return;results.replaceChildren();
    const found=modes.filter(v=>!q||v.join(' ').toLowerCase().includes(q));
    for(const [mode,label,description] of found){const b=document.createElement('button');b.type='button';b.className='command-result';b.setAttribute('role','option');const s=document.createElement('strong');s.textContent=label;const t=document.createElement('small');t.textContent=description;b.append(s,t);b.addEventListener('click',()=>go(mode));results.append(b);}
    if(!found.length){const p=document.createElement('p');p.textContent='No matching workspace sections.';p.className='command-empty';results.append(p);}
  }
  function search(){lastFocus=document.activeElement;setOpen(overlay,true);paint();input?.focus();}
  byId('quick-search')?.addEventListener('click',search);
  byId('command-close')?.addEventListener('click',()=>setOpen(overlay,false));
  input?.addEventListener('input',paint);
  input?.addEventListener('keydown',e=>{if(e.key==='Enter'){const first=results?.querySelector('.command-result');if(first){e.preventDefault();first.click();}}});
  overlay?.addEventListener('mousedown',e=>{if(e.target===overlay)setOpen(overlay,false);});
  for(const el of document.querySelectorAll('[data-go]'))el.addEventListener('click',()=>go(el.dataset.go));
  document.addEventListener('keydown',e=>{
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();search();}
    if(e.key==='Escape'){setOpen(overlay,false);setOpen(prefs,false);}
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'&&!byId('workspace')?.classList.contains('hidden')&&document.querySelector('[data-mode="code"]')?.classList.contains('active')){e.preventDefault();const save=byId('save-file');if(save&&!save.disabled)save.click();}
  });
  const editor=byId('file-content'),dirty=byId('dirty-indicator');
  const isDirty=()=>Boolean(editor&&window.kyroCleanContent!==undefined&&editor.value!==window.kyroCleanContent&&!byId('workspace')?.classList.contains('hidden'));
  editor?.addEventListener('input',()=>dirty?.classList.toggle('hidden',!isDirty()));
  for(const id of ['file-list','project-list'])byId(id)?.addEventListener('click',e=>{
    if(!isDirty())return;
    const target=e.target.closest('button');if(!target)return;
    if(!confirm('You have unsaved changes. Discard them and continue?')){e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();}
    else {window.kyroCleanContent=editor.value;dirty?.classList.add('hidden');}
  },true);
  window.addEventListener('beforeunload',e=>{if(isDirty()){e.preventDefault();e.returnValue='';}});
  byId('file-filter')?.addEventListener('input',()=>{
    const q=byId('file-filter').value.trim().toLowerCase();
    let count=0;for(const b of byId('file-list')?.querySelectorAll('button.file-entry')||[]){const ok=b.textContent.toLowerCase().includes(q);b.hidden=!ok;if(ok)count++;}
  });
  function loadSettings(){
    try{return JSON.parse(localStorage.getItem('kyro-display-v1')||'{}');}catch{return {};}
  }
  const compact=byId('compact-toggle'),motion=byId('motion-toggle');
  function apply(){document.body.classList.toggle('compact-ui',Boolean(compact?.checked));document.body.classList.toggle('reduce-motion',Boolean(motion?.checked));}
  const st=loadSettings();if(compact)compact.checked=Boolean(st.compact);if(motion)motion.checked=Boolean(st.motion);apply();
  function changed(){apply();try{localStorage.setItem('kyro-display-v1',JSON.stringify({compact:compact.checked,motion:motion.checked}));}catch{}}
  compact?.addEventListener('change',changed);motion?.addEventListener('change',changed);
  byId('prefs-button')?.addEventListener('click',()=>{lastFocus=document.activeElement;setOpen(prefs,true);compact?.focus();});
  byId('prefs-close')?.addEventListener('click',()=>setOpen(prefs,false));
  prefs?.addEventListener('mousedown',e=>{if(e.target===prefs)setOpen(prefs,false);});
});
