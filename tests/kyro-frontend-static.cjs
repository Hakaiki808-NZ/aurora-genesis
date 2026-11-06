/** Kyro frontend static contract smoke checks: no dependencies. */
'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const dir=require('node:path').join(__dirname,'..','cloud','workspace-v5');
const load=n=>fs.readFileSync(require('node:path').join(dir,n),'utf8');
const html=load('index.html'), css=load('styles.css'), app=load('app.js'), ux=load('ux.js');
const preview=load('preview.html'), pcss=load('preview.css'), pjs=load('preview.js'), light=load('light.css');
const checks=[
['auth callback remains scoped to private workspace',()=>{assert.match(app,/kyro-v4-private-/);assert.match(app,/\/v3\/index\.html/);}],
['protected API requests require the JWT',()=>assert.match(app,/Authorization:'Bearer '\+state\.token/)],
['all major workspace modes implemented',()=>['overview','code','collab','chat','connectors'].forEach(id=>{assert.match(html,new RegExp('id="'+id+'-panel"'));assert.match(app,new RegExp("'"+id+"'"));})],
['workspace search and settings hooked up',()=>['command-overlay','prefs-overlay','quick-search','prefs-button','file-filter','dirty-indicator'].forEach(id=>assert.match(html,new RegExp('id="'+id+'"')))],
['visual overview and nonproduction engine disclosure',()=>{assert.match(html,/AURORA · ENGINE/);assert.match(html,/NOT CONNECTED/);assert.match(css,/\.overview-metrics/);}],
['secure frontend renders model content as text',()=>{assert.match(app,/textContent/);assert.doesNotMatch(app,/innerHTML\s*=/);}],
['untrusted preview contains no live API and is read-only',()=>{assert.match(preview,/Illustrative preview/);assert.match(preview,/read-only/);assert.doesNotMatch(pjs,/fetch\s*\(/);assert.doesNotMatch(pjs,/Authorization/);assert.match(pcss,/\.preview-hero/);}],
['no inline scripts in CSP-protected pages',()=>{assert.doesNotMatch(html,/<script(?:\s[^>]*)?>[^<]+<\/script>/);assert.doesNotMatch(preview,/<script(?:\s[^>]*)?>[^<]+<\/script>/);}],
['preview references complete assets',()=>{for(const asset of ['preview.js','preview.css','styles.css'])assert.ok(preview.includes('/v3/'+asset));}],
['silver light theme is applied to workspace and preview',()=>{for(const page of [html,preview]){assert.match(page,/\/v3\/light\.css/);assert.match(page,/name="theme-color" content="#f2f5f7"/);}assert.match(light,/color-scheme:light/);assert.match(light,/\.preview-page/);assert.match(light,/\.command-dialog/);assert.match(light,/focus-visible/);}],
['remaining disclosures are explicit',()=>{assert.match(preview,/experimental research/i);assert.match(html,/Protected engine not attached|Aurora execution not attached/);}],
];
let count=0;
for(const [name,run] of checks){run();process.stdout.write('PASS '+name+'\n');count++;}
console.log(count+' Kyro frontend static checks passed.');
