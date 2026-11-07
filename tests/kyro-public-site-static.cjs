'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const dir=path.join(__dirname,'..','cloud','public-site-v1');
const routes=['index','blog','developers','dev-login','docs','modules','collaboration','roadmap','about','status','privacy','community','404'];
for(const name of routes){
 const html=fs.readFileSync(path.join(dir,name+'.html'),'utf8');
 for(const token of ['id="main"','name="viewport"','content="noindex,nofollow"','./site.css','./site.js']){
  assert.ok(html.includes(token),name+' missing '+token);
 }
}
const js=fs.readFileSync(path.join(dir,'site.js'),'utf8');
const css=fs.readFileSync(path.join(dir,'site.css'),'utf8');
for(const key of ['blog','developers','login','docs','modules','collaboration','roadmap','about','status','privacy']){
 assert.ok(js.includes(''+key), 'missing '+key+' route');
}
assert.match(js,/\/v3\/index\.html/,'links to real Cognito-protected workspace');
assert.match(js,/early-access-interest\\.yml/,'public GitHub interest form exists in community page');
assert.match(js,/const community=/,'community content wired to router');
assert.match(js,/data-blog-filter/);
assert.match(js,/data-module-filter/);
assert.match(js,/data-role/);
assert.match(js,/data-roadmap-filter/);
assert.match(js,/addEventListener/);
assert.match(css,/@media/);
assert.match(css,/prefers-reduced-motion/);
assert.doesNotMatch(js,/localStorage|sessionStorage|eval\s*\(/);
console.log('PASS: Kyro public site routes, alpha disclosures, navigation and interactive contracts.');
