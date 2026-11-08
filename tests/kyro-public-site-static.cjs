'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const dir=path.join(__dirname,'..','cloud','public-site-v1');
const routes=['index','blog','modules','collaboration','roadmap','about','status','privacy','community','404'];
for(const name of routes){
 const html=fs.readFileSync(path.join(dir,name+'.html'),'utf8');
 for(const token of ['id="main"','name="viewport"','content="noindex,nofollow"','./site.css','./site.js']){
  assert.ok(html.includes(token),name+' missing '+token);
 }
}
for(const name of ['developers','dev-login','docs','api']){
 const html=fs.readFileSync(path.join(dir,name+'.html'),'utf8');
 assert.match(html,/Public developer tools and documentation are not available/);
 assert.doesNotMatch(html,/<script\\b/i);
}
const js=fs.readFileSync(path.join(dir,'site.js'),'utf8');
const css=fs.readFileSync(path.join(dir,'site.css'),'utf8');
for(const key of ['blog','developers','login','docs','modules','collaboration','roadmap','about','status','privacy']){
 assert.ok(js.includes(''+key), 'missing '+key+' route');
}
assert.match(js,/\/v3\/index\.html/,'links to real Cognito-protected workspace');
assert.match(js,/early-access-interest\.yml/,'public GitHub interest form exists in community page');
assert.match(js,/const community=/,'community content wired to router');
assert.match(js,/data-blog-filter/);
assert.match(js,/data-module-filter/);
assert.match(js,/data-role/);
assert.match(js,/data-roadmap-filter/);
assert.match(js,/addEventListener/);
assert.match(css,/@media/);
assert.match(css,/prefers-reduced-motion/);
assert.doesNotMatch(js,/localStorage|sessionStorage|eval\s*\(/);
// Public discovery must stay separate from account-backed app navigation.
assert.match(js,/details class="nav-group"/,'grouped accessible dropdowns required');
assert.match(js,/const navGroups=/,'keyboard/mobile-aware menu control required');
assert.match(js,/\/v3\/index\.html\?profile=1/,'public sign-in must open profile-first entry');
const kyroHtml=fs.readFileSync(path.join(__dirname,'..','web','kyro','v3','index.html'),'utf8');
const kyroJs=fs.readFileSync(path.join(__dirname,'..','web','kyro','v3','app.js'),'utf8');
for(const id of ['profile-panel','profile-name','profile-project-count','launch-kyro-app'])assert.ok(kyroHtml.includes('id="'+id+'"'),'missing Kyro profile component '+id);
assert.match(kyroHtml,/data-mode="profile"/);
assert.match(kyroJs,/kyro-v3-entry-intent/,'must retain login destination across Cognito callback');
assert.match(kyroJs,/window\.open\('\/v3\/index\.html\?app=1'/,'app should be launched via explicit user action');
assert.match(kyroJs,/show\(intended\)/,'login must route to profile or app based on entry');
assert.doesNotMatch(js,/localStorage|sessionStorage|eval\s*\(/);
console.log('PASS: Kyro public navigation, secure profile-first login and app-launch contracts.');
