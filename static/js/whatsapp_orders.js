document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('whatsapp-product-form');
  const variant = document.getElementById('volume-select');
  const quantity = document.getElementById('quantity-input');
  if (form && variant && quantity) {
    const params = new URLSearchParams(window.location.search);
    const option = Array.from(variant.options).find(option => option.value === params.get('volume_id'));
    if (option && Number(option.dataset.stock) > 0) {
      variant.value = option.value;
      variant.dispatchEvent(new Event('change'));
      const requested = params.get('quantity');
      if (/^[1-9]\d*$/.test(requested || '')) quantity.value = requested;
    }
    const sync = function () {
      form.elements.volume_id.value = variant.value;
      form.elements.quantity.value = quantity.value;
      const selected = variant.options[variant.selectedIndex];
      form.querySelector('button').disabled = !variant.value || Number(selected.dataset.stock) <= 0 || !quantity.validity.valid;
    };
    variant.addEventListener('change', sync);
    quantity.addEventListener('input', sync);
    form.addEventListener('submit', function (event) {
      sync();
      if (!variant.reportValidity() || !quantity.reportValidity()) event.preventDefault();
    });
    sync();
  }

  let timer, controller, pending = false;
  function showStatus(text) { const status = document.querySelector('[data-wa-status]'); if (status) status.textContent = text; }
  async function updateSummary() {
    const form = document.querySelector('.wa-quantity-form');
    if (!form || !form.reportValidity()) return;
    controller?.abort();
    controller = new AbortController();
    const current = controller;
    const url = new URL(window.location.href);
    url.search = new URLSearchParams(new FormData(form)).toString();
    pending = true;
    showStatus('Updating…');
    try {
      const response = await fetch(url, {signal: current.signal, credentials: 'same-origin'});
      if (!response.ok) throw new Error('Update failed');
      const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
      if (current !== controller) return;
      const replacement = doc.querySelector('.wa-grid');
      if (!replacement) throw new Error('Quantity unavailable');
      document.querySelector('.wa-grid').replaceWith(replacement);
      history.replaceState(null, '', url);
      pending = false;
      showStatus('Updated');
    } catch (error) {
      if (error.name !== 'AbortError') showStatus('Could not update. Adjust the quantity to try again.');
    }
  }
  document.addEventListener('input', function (event) {
    if (event.target.id !== 'wa-quantity') return;
    pending = true;
    clearTimeout(timer);
    timer = setTimeout(updateSummary, 350);
  });
  document.addEventListener('submit', function (event) {
    if (!event.target.matches('.wa-quantity-form')) return;
    event.preventDefault(); clearTimeout(timer); updateSummary();
  });
  document.addEventListener('click', async function (event) {
    const step = event.target.closest('[data-wa-step]');
    if (step) {
      const input = document.getElementById('wa-quantity');
      const value = Math.min(Number(input.max), Math.max(1, Number(input.value || 1) + Number(step.dataset.waStep)));
      if (value === Number(input.value)) return;
      input.value = value; clearTimeout(timer); updateSummary(); return;
    }
    const link = event.target.closest('a');
    const copy = event.target.closest('[data-copy-order]');
    if ((link?.href.startsWith('https://wa.me/') || copy) && pending) {
      event.preventDefault(); showStatus('Wait for the quantity update before continuing.'); return;
    }
    if (copy) {
      const message = document.getElementById('wa-message');
      const status = document.querySelector('[data-copy-status]');
      try { await navigator.clipboard.writeText(message.value); status.textContent = 'Message copied.'; }
      catch (error) { message.focus(); message.select(); status.textContent = 'Select and copy the message.'; }
    }
  });
});
