/** Kyro cross-platform contract checks; no dependencies or credentials. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.join(__dirname,'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const web='cloud/workspace-v5/',native='apps/kyro-mobile/';
const html=read(web+'index.html'),preview=read(web+'preview.html');
const css=read(web+'mobile.css'),js=read(web+'mobile.js');
const manifest=JSON.parse(read(web+'manifest.webmanifest'));
const worker=read(web+'service-worker.js');
const app=read(native+'App.tsx'),client=read(native+'src/client.ts');
const config=JSON.parse(read(native+'app.json'));
const checks=[
 ['both web pages load the mobile CSS and manifest',()=>{for(const page of [html,preview]){assert.match(page,/\/v3\/mobile\.css/);assert.match(page,/\/v3\/manifest\.webmanifest/);}}],
 ['mobile project drawer has a real accessible trigger',()=>{assert.match(html,/id="mobile-projects"/);assert.match(html,/aria-expanded="false"/);assert.match(js,/setAttribute\('aria-expanded'/);assert.match(css,/\.mobile-menu-open/);}],
 ['responsive phone navigation and touch layouts',()=>{assert.match(css,/@media\(max-width:760px\)/);assert.match(css,/grid-template-columns:repeat\(5/);assert.match(css,/env\(safe-area-inset-bottom/);}],
 ['web manifest is scoped and linked',()=>{assert.equal(manifest.scope,'/v3/');assert.equal(manifest.start_url,'/v3/index.html');assert.equal(manifest.display,'standalone');assert.match(manifest.icons[0].src,/kyro-icon\.svg/);}],
 ['service worker excludes API, login and protected pages',()=>{assert.match(worker,/request\.mode==='navigate'/);assert.match(worker,/url\.origin!==self\.location\.origin/);assert.match(worker,/ALLOWED\.has\(url\.pathname\)/);assert.doesNotMatch(worker,/\/api\/v3\/|\/oauth2\//);}],
 ['Expo scheme and platform identities defined',()=>{assert.equal(config.expo.scheme,'kyro');assert.ok(config.expo.ios.bundleIdentifier);assert.ok(config.expo.android.package);}],
 ['mobile uses Cognito authorization code and PKCE',()=>{assert.match(app,/useAuthRequest/);assert.match(app,/ResponseType\.Code/);assert.match(app,/usePKCE:true/);assert.match(app,/code_verifier/);assert.match(app,/exchangeCodeAsync/);}],
 ['native login gated until dedicated Cognito client is configured',()=>{assert.match(app,/!isConfigured/);assert.match(client,/EXPO_PUBLIC_COGNITO_CLIENT_ID/);assert.doesNotMatch(client,/client_secret|clientSecret/);}],
 ['native calls same protected v3 endpoint with in-memory identity',()=>{assert.match(client,/\/api\/v3/);assert.match(client,/Authorization:'Bearer '/);assert.match(app,/kyroApi<\{subject:string\}>\(tokens\.idToken,'\/me'\)/);assert.doesNotMatch(app,/AsyncStorage|localStorage|SecureStore/);}],
 ['model content remains text and engine execution restricted',()=>{assert.match(app,/Genesis is a research reference/);assert.match(app,/Aurora execution is controlled separately/);assert.doesNotMatch(app,/WebView|eval\s*\(/);}],
 ['all five workspace modes are represented',()=>{for(const tab of ["home","chat","code","team","tools"])assert.match(app,new RegExp("id:'"+tab+"'"));}],
];
for(const [name,test] of checks){test();process.stdout.write('PASS '+name+'\n');}
console.log(checks.length+' mobile platform checks passed.');
