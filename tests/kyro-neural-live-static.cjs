// Static, offline guardrail for the *current* deployed Kyro V5 neural panel.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '../web/kyro/v3');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
const neural = fs.readFileSync(path.join(root, 'neural.js'), 'utf8');

assert.match(html, /<script[^>]+src="\/v3\/app\.js"/);
assert.match(html, /<script[^>]+src="\/v3\/neural\.js"/);
for (const id of ['neural-form', 'neural-input', 'neural-check', 'neural-status', 'neural-answer', 'neural-detail']) {
  assert.ok(html.includes('id="' + id + '"'), 'missing neural field: ' + id);
}
assert.match(app, /async function api\(path,method='GET',body=null\)/);
assert.match(app, /Authorization:'Bearer '\+state\.token/);
assert.match(app, /\/api\/v3/);
assert.match(neural, /window\.api\('\/neural\/status'\)/);
assert.match(neural, /window\.api\('\/neural\/chat', 'POST', \{ message \}\)/);
assert.match(neural, /data\.service !== 'genesis-neural-research'/);
assert.match(neural, /answer\.textContent = data\.answer/);
assert.doesNotMatch(neural, /\.innerHTML\s*=/, 'model output must not be rendered as HTML');

// Browser classic-script global function declarations are exposed on window;
// do not require or inject a separate assignment (which can make drift worse).
const events = [];
const context = {document: {addEventListener: (name, fn) => events.push(name)}};
context.window = context;
vm.createContext(context);
vm.runInContext(app, context, {filename: 'app.js'});
assert.equal(typeof context.api, 'function');
vm.runInContext(neural, context, {filename: 'neural.js'});
assert.deepEqual(events, ['DOMContentLoaded', 'DOMContentLoaded']);
console.log('KYRO_V5_NEURAL_STATIC=PASS');
