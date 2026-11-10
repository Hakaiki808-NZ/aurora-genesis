(() => {
  'use strict';
  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('neural-form');
    const input = document.getElementById('neural-input');
    const answer = document.getElementById('neural-answer');
    const detail = document.getElementById('neural-detail');
    const status = document.getElementById('neural-status');
    const check = document.getElementById('neural-check');
    if (!form || !input || !answer || !detail || !status || !check) return;
    let busy = false;
    check.addEventListener('click', async () => {
      if (busy) return;
      status.textContent = 'Checking neural model…';
      try {
        const data = await window.api('/neural/status');
        status.textContent = `${data.base || 'Genesis'} · ${data.status || 'research'} · ${data.limits?.monthly_total_requests || '?'} monthly attempts maximum`;
      } catch (error) {
        status.textContent = `Model status unavailable: ${error.message || String(error)}`;
      }
    });
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message || busy) return;
      busy = true;
      const send = form.querySelector('button[type="submit"]');
      if (send) send.disabled = true;
      answer.textContent = 'Genesis is generating a response…';
      detail.textContent = 'Neural model · research only · no tools or Engine execution';
      try {
        const data = await window.api('/neural/chat', 'POST', { message }, 110000);
        if (data.service !== 'genesis-neural-research' || typeof data.answer !== 'string') {
          throw new Error('Unexpected neural model response');
        }
        answer.textContent = data.answer;
        detail.textContent = `${data.model || 'Genesis neural research'} · ${data.chosen_action || 'research'} · not saved to chat archive`;
        input.value = '';
      } catch (error) {
        answer.textContent = `Neural research request failed: ${error.message || String(error)}`;
      } finally {
        busy = false;
        if (send) send.disabled = false;
      }
    });
  });
})();