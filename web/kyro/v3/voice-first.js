'use strict';
// Kyro V3 voice-first entry point. Reuses the existing authenticated
// chat speech controls; no engine commands or separate microphone stream.
(() => {
  const byId = (id) => document.getElementById(id);
  const setup = () => {
    const workspace = byId('workspace');
    const voiceStart = byId('voice-start');
    const voiceStop = byId('voice-stop');
    const status = byId('voice-status');
    const autoSend = byId('voice-auto-send');
    const readReplies = byId('voice-read-replies');
    const chat = byId('chat-input');
    if (!workspace || !voiceStart || !voiceStop || !status || !chat) return;

    const panel = document.createElement('section');
    panel.className = 'kyro-vfc';
    panel.setAttribute('aria-label', 'Kyro voice-first console');
    panel.innerHTML = [
      '<div class="kyro-vfc-eyebrow">KYRO · VOICE FIRST</div>',
      '<div class="kyro-vfc-grid">',
      ' <div class="kyro-vfc-orb" aria-hidden="true"><span>◉</span></div>',
      ' <div class="kyro-vfc-body">',
      '   <h2>Speak to your workspace.</h2>',
      '   <p>Ask Genesis questions by voice, then choose whether to review or send your transcript.</p>',
      '   <div class="kyro-vfc-actions">',
      '     <button type="button" class="kyro-vfc-primary" id="vfc-talk">🎙 Talk to Kyro</button>',
      '     <button type="button" id="vfc-stop">■ Stop</button>',
      '     <button type="button" id="vfc-chat">Open conversation</button>',
      '   </div>',
      '   <div class="kyro-vfc-options">',
      '     <label><input id="vfc-automatic" type="checkbox"> Send transcript automatically</label>',
      '     <label><input id="vfc-spoken" type="checkbox"> Read answers aloud</label>',
      '   </div>',
      '   <div class="kyro-vfc-status" id="vfc-status" role="status">Microphone off — activate when ready</div>',
      ' </div>',
      '</div>',
      '<p class="kyro-vfc-disclosure">Speech recognition depends on browser support and may be processed by your browser provider. This panel does not connect Aurora or provide system-wide listening.</p>'
    ].join('');
    workspace.prepend(panel);
    const sync = () => {
      byId('vfc-status').textContent = status.textContent || 'Microphone off';
      const active = /listening/i.test(status.textContent || '');
      panel.classList.toggle('kyro-vfc-active', active);
      byId('vfc-automatic').checked = Boolean(autoSend?.checked);
      byId('vfc-spoken').checked = Boolean(readReplies?.checked);
    };
    const navChat = () => {
      const nav = document.querySelector('button.nav[data-mode="chat"]');
      nav?.click();
    };
    byId('vfc-talk').addEventListener('click', () => {
      navChat();
      voiceStart.click();
      sync();
    });
    byId('vfc-stop').addEventListener('click', () => { voiceStop.click(); sync(); });
    byId('vfc-chat').addEventListener('click', () => { navChat(); chat.focus(); });
    byId('vfc-automatic').addEventListener('change', (event) => {
      if (autoSend) autoSend.checked = event.target.checked;
      sync();
    });
    byId('vfc-spoken').addEventListener('change', (event) => {
      if (readReplies) readReplies.checked = event.target.checked;
      sync();
    });
    autoSend?.addEventListener('change', sync);
    readReplies?.addEventListener('change', sync);
    new MutationObserver(sync).observe(status, { childList: true, characterData: true, subtree: true });
    // Voice output is the preferred default. Auto-send stays opt-in.
    if (readReplies) readReplies.checked = true;
    sync();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
  else setup();
})();