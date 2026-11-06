(() => {
  'use strict';
  let token = '';
  let busy = false;
  const el = (id) => document.getElementById(id);
  const status = el('status');
  const send = el('send');
  const input = el('message');

  function addMessage(role, content) {
    const item = document.createElement('div');
    item.className = 'bubble ' + role;
    item.textContent = content; // Never interpret model output as markup.
    el('messages').appendChild(item);
    item.scrollIntoView({block:'end',behavior:'smooth'});
  }

  async function request(path, options) {
    const res = await fetch(path, Object.assign({}, options || {}, {
      headers: Object.assign({
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      }, (options || {}).headers || {})
    }));
    if (!res.ok) throw new Error(res.status === 401 ? 'Access denied' : 'Request failed (' + res.status + ')');
    return res.json();
  }

  el('unlock').addEventListener('click', async () => {
    const candidate = el('token').value;
    if (!candidate || candidate.length < 24) {
      status.textContent = 'Enter the complete launch token.';
      return;
    }
    token = candidate;
    try {
      const result = await request('/api/status');
      el('token').value = '';
      status.textContent = result.model + ' ' + result.model_version + ' ready · Aurora not attached';
      send.disabled = false;
      input.focus();
    } catch (err) {
      token = '';
      send.disabled = true;
      status.textContent = err.message;
    }
  });

  el('chat-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!token || busy) return;
    const message = input.value.trim();
    if (!message) return;
    busy = true;
    send.disabled = true;
    input.value = '';
    addMessage('user', message);
    try {
      const result = await request('/api/chat', {
        method: 'POST',
        body: JSON.stringify({message:message})
      });
      addMessage('assistant', String(result.answer || 'No response'));
    } catch (err) {
      addMessage('assistant', 'Request error: ' + err.message);
      if (err.message === 'Access denied') token = '';
    } finally {
      busy = false;
      send.disabled = !token;
    }
  });
})();
