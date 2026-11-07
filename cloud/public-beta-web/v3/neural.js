'use strict';
/* Research-only neural responses. Uses the existing in-memory Kyro JWT,
   never localStorage and never grants Aurora execution privileges. */
(() => {
  const get=id=>document.getElementById(id);
  const status=txt=>{const el=get('neural-status');if(el)el.textContent=String(txt);};
  const answer=txt=>{const el=get('neural-answer');if(el)el.textContent=String(txt);};
  window.kyroNeuralLoad=async()=>{
    status('Checking the protected Genesis inference route…');
    const b=get('neural-send');if(b)b.disabled=true;
    try{
      const d=await api('/neural/status');
      status(d.status==='candidate_inference_available'
        ? 'Private neural candidate online · '+d.base+' + '+d.adapter+
          ' · max '+d.limits.daily_per_user+' attempts/day'
        : 'Neural inference status: '+String(d.status||'unknown'));
    }catch(e){status('Research inference not yet reachable: '+String(e.message||e));}
    finally{if(b)b.disabled=false;}
  };
  const setup=()=>{
    const form=get('neural-form');if(!form)return;
    form.onsubmit=async e=>{
      e.preventDefault();
      const input=get('neural-input'),btn=get('neural-send');
      const message=(input.value||'').trim();
      if(!message){status('Enter a question first.');return;}
      if(message.length>2500){status('Please use 2500 characters or fewer.');return;}
      btn.disabled=true;answer('');status('Genesis is reasoning in private research mode…');
      try{
        // API Gateway has a separate bounded integration time limit.
        const data=await api('/neural/chat','POST',{message},35000);
        answer(data.answer||'The model returned no answer.');
        status('Experimental: '+String(data.model||'Genesis candidate')+
          ' · Action '+String(data.chosen_action||'none')+
          ' · Aurora execution disabled');
      }catch(err){
        status('Inference request failed: '+String(err.message||err));
      }finally{btn.disabled=false;}
    };
    for(const b of document.querySelectorAll('[data-neural-prompt]')){
      b.addEventListener('click',()=>{
        get('neural-input').value=b.getAttribute('data-neural-prompt')||'';
        get('neural-input').focus();
      });
    }
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});
  else setup();
})();
