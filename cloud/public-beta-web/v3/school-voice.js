'use strict';
(()=>{
 const byId=id=>document.getElementById(id);
 const schoolCases=new Map();let recognition=null;
 function schoolStatus(message){const el=byId('school-feedback');if(el)el.textContent=message;}
 function currentCase(){return schoolCases.get(byId('school-case')?.value);}
 function showCase(){
  const item=currentCase(),title=byId('school-question'),opts=byId('school-options');
  opts?.replaceChildren();schoolStatus('Choose the best response. Answers are evaluated against fixed reference cases.');
  if(!item){if(title)title.textContent='No exercises loaded';return;}
  title.textContent=item.domain+' · '+item.question;
  item.options.forEach((answer,i)=>{
   const label=document.createElement('label');label.className='school-choice';
   const radio=document.createElement('input');radio.type='radio';radio.name='school-answer';radio.value=String(i);
   label.append(radio,document.createTextNode(' '+answer));opts.append(label);
  });
 }
 async function history(){
  const d=await api('/realignment/history'),el=byId('school-history');if(!el)return;
  el.replaceChildren();const h=document.createElement('strong');h.textContent='Recent practice · '+d.correct+'/'+d.count+' correct';el.append(h);
  for(const a of d.attempts||[]){
   const p=document.createElement('p');p.className='school-attempt';
   p.textContent=(a.correct?'✓ ':'↺ ')+a.case_id+' · '+new Date(Number(a.created_at)*1000).toLocaleString();el.append(p);
  }
  if(!d.count){const p=document.createElement('p');p.textContent='No practice attempts yet.';el.append(p);}
 }
 window.kyroSchoolLoad=async()=>{
  const data=await api('/realignment/curriculum');
  const select=byId('school-case');if(!select)return;
  schoolCases.clear();select.replaceChildren();
  for(const item of data.cases||[]){
   schoolCases.set(item.id,item);
   const opt=document.createElement('option');opt.value=item.id;opt.textContent=item.domain+' — '+item.id;select.append(opt);
  }
  showCase();await history();
 };
 function setVoiceStatus(s){const el=byId('voice-status');if(el)el.textContent=s;}
 function stopVoice(){try{recognition?.stop();}catch{} recognition=null;setVoiceStatus('Microphone off');}
 function startVoice(){
  if(!state.token){setVoiceStatus('Sign in first');return;}
  const Rec=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!Rec){setVoiceStatus('Speech recognition is not supported by this browser');return;}
  if(recognition)stopVoice();
  const r=new Rec();recognition=r;r.lang='en-NZ';r.continuous=false;r.interimResults=false;r.maxAlternatives=1;
  r.onresult=e=>{
   const transcript=String(e.results?.[0]?.[0]?.transcript||'').trim().slice(0,3000);
   if(!transcript)return;
   const input=byId('chat-input');if(input){input.value=transcript;input.focus();}
   setVoiceStatus('Transcribed. Review and send, or enable auto-send.');
   if(byId('voice-auto-send')?.checked)byId('chat-form')?.requestSubmit();
  };
  r.onerror=e=>setVoiceStatus('Voice input: '+String(e.error||'unavailable'));
  r.onend=()=>{recognition=null;if(byId('voice-status')?.textContent==='Listening…')setVoiceStatus('Microphone off');};
  try{r.start();setVoiceStatus('Listening…');}catch{recognition=null;setVoiceStatus('Unable to start microphone');}
 }
 function speakLast(force=false){
  if(!force&&!byId('voice-read-replies')?.checked)return;
  if(!('speechSynthesis' in window)){setVoiceStatus('Speech playback unavailable');return;}
  const rows=[...document.querySelectorAll('#messages .post')].reverse();
  const row=rows.find(x=>/assistant|genesis/i.test(x.querySelector('strong')?.textContent||''));
  const text=row?.querySelector('div')?.textContent?.trim();
  if(!text){setVoiceStatus('No Genesis reply to speak');return;}
  speechSynthesis.cancel();
  const utterance=new SpeechSynthesisUtterance(text.slice(0,5000));utterance.lang='en-NZ';utterance.rate=1;
  const voices=speechSynthesis.getVoices();const selected=byId('voice-choice')?.value;
  utterance.voice=voices.find(v=>v.voiceURI===selected)||voices.find(v=>v.lang.toLowerCase()==='en-nz')||null;
  speechSynthesis.speak(utterance);setVoiceStatus('Speaking Genesis reply…');
 }
 window.kyroVoiceAfterReply=()=>speakLast(false);
 function fillVoices(){
  const select=byId('voice-choice');if(!select||!('speechSynthesis' in window))return;
  const chosen=select.value;select.replaceChildren();
  for(const voice of speechSynthesis.getVoices().filter(v=>/^en/i.test(v.lang))){
   const o=document.createElement('option');o.value=voice.voiceURI;o.textContent=voice.name+' ('+voice.lang+')';select.append(o);
  }
  if(chosen&&[...select.options].some(o=>o.value===chosen))select.value=chosen;
  else {const preferred=[...select.options].find(o=>o.textContent.includes('(en-NZ)'));if(preferred)select.value=preferred.value;}
 }
 document.addEventListener('DOMContentLoaded',()=>{
  byId('school-case')?.addEventListener('change',showCase);
  byId('school-form')?.addEventListener('submit',async event=>{
   event.preventDefault();const item=currentCase(),answer=document.querySelector('input[name="school-answer"]:checked');
   if(!item||!answer){schoolStatus('Choose one response first.');return;}
   const button=byId('school-submit');button.disabled=true;
   try{
    const outcome=await api('/realignment/attempt','POST',{case_id:item.id,choice:Number(answer.value)});
    schoolStatus((outcome.correct?'✓ Correct. ':'↺ Review required. ')+outcome.feedback);
    await history();
   }catch(e){schoolStatus(e.message||String(e));}finally{button.disabled=false;}
  });
  byId('voice-start')?.addEventListener('click',startVoice);
  byId('voice-stop')?.addEventListener('click',()=>{stopVoice();window.speechSynthesis?.cancel();});
  byId('voice-play-last')?.addEventListener('click',()=>speakLast(true));
  if(!('SpeechRecognition' in window)&&!('webkitSpeechRecognition' in window)){byId('voice-start').disabled=true;setVoiceStatus('This browser has no speech recognition support. Text chat remains available.');}
  if('speechSynthesis' in window){fillVoices();speechSynthesis.addEventListener?.('voiceschanged',fillVoices);}
 });
})();
