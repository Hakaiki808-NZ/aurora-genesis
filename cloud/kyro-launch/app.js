(()=>{
"use strict";
// Public, read-only catalogue: this script does not purchase, authenticate, track,
// upload, or install a module into a cloud account.
const grid=document.getElementById("module-grid");
const status=document.getElementById("catalog-status");
const buttons=[...document.querySelectorAll("[data-filter]")];
let catalogue=[];
let filter="all";

function node(tag,text,cls){
  const el=document.createElement(tag);
  if(text!==undefined)el.textContent=String(text);
  if(cls)el.className=cls;
  return el;
}

function safePack(raw){
  if(!raw||typeof raw!=="object"||raw.price!=="Free"||!["language","knowledge"].includes(raw.category))return null;
  if(typeof raw.href!=="string"||!/^https:\/\/github\.com\/Hakaiki808-NZ\/aurora-genesis\/blob\/main\/examples\/modules\/[a-z0-9-]+\.json$/.test(raw.href))return null;
  for(const key of ["id","title","description","language","icon","availability"]){
    if(typeof raw[key]!=="string"||raw[key].length>350)return null;
  }
  if(!Number.isInteger(raw.chapters)||raw.chapters<1||raw.chapters>250)return null;
  return raw;
}

function card(pack){
  const article=node("article",undefined,"module-card");
  const head=node("div",undefined,"module-head");
  head.append(node("span",pack.icon,"module-symbol"),node("span","FREE","price-tag"));
  article.append(head,node("span",pack.category==="language"?"Language pack":"Knowledge pack","module-category"));
  const title=node("h3",pack.title);
  article.append(title,node("p",pack.description));
  const meta=node("div",pack.language+" · "+pack.chapters+" starter topics","module-meta");
  const link=node("a","View pack source ↗","module-link");
  link.href=pack.href;link.rel="noopener noreferrer";link.target="_blank";
  link.setAttribute("aria-label","View "+pack.title+" open-source reference pack on GitHub");
  article.append(meta,link);
  return article;
}

function render(){
  grid.replaceChildren();
  const shown=catalogue.filter(pack=>filter==="all"||pack.category===filter);
  for(const pack of shown)grid.append(card(pack));
  if(!shown.length)grid.append(node("p","No starter packs in this category yet.","loading"));
  status.textContent=shown.length+" free starter "+(shown.length===1?"pack":"packs")+" shown · Reference code only; no cloud installation";
  for(const button of buttons){
    const active=button.dataset.filter===filter;
    button.classList.toggle("active",active);
    button.setAttribute("aria-pressed",String(active));
  }
}

for(const button of buttons)button.addEventListener("click",()=>{
  filter=button.dataset.filter||"all";render();
});

async function load(){
  try{
    const response=await fetch("./catalog.json",{cache:"no-store"});
    if(!response.ok)throw new Error("Catalogue unavailable");
    const payload=await response.json();
    if(payload?.schema_version!==1||!Array.isArray(payload.modules))throw new Error("Catalogue format unavailable");
    catalogue=payload.modules.map(safePack).filter(Boolean);
    if(!catalogue.length)throw new Error("Catalogue empty");
    render();
  }catch(_error){
    grid.replaceChildren(node("p","The module catalogue could not load. Explore the open-source packs through the research repository.","loading"));
    status.replaceChildren();
    const link=node("a","View GitHub examples ↗","module-link");
    link.href="https://github.com/Hakaiki808-NZ/aurora-genesis/tree/main/examples/modules";
    link.rel="noopener noreferrer";
    grid.append(link);
  }
}
load();
})();