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
  const reviewQuantity = document.getElementById('wa-quantity');
  if (reviewQuantity) {
    const initialQuantity = reviewQuantity.value;
    reviewQuantity.addEventListener('input', function () {
      const status = document.querySelector('[data-copy-status]');
      if (reviewQuantity.value !== initialQuantity) {
        document.querySelector('.wa-fallback').open = true;
        status.textContent = 'Use Update summary to apply your new quantity before continuing or copying.';
      } else status.textContent = '';
    });
    document.querySelectorAll('a[href^="https://wa.me/"]').forEach(function (link) {
      link.addEventListener('click', function (event) {
        if (reviewQuantity.value !== initialQuantity) {
          event.preventDefault();
          reviewQuantity.form.querySelector('button').focus();
          reviewQuantity.form.reportValidity();
          document.querySelector('[data-copy-status]').textContent = 'Use Update summary to apply your new quantity before continuing.';
          document.querySelector('.wa-fallback').open = true;
        }
      });
    });
  }
  const copy = document.querySelector('[data-copy-order]');
  if (copy) copy.addEventListener('click', async function () {
    const message = document.getElementById('wa-message');
    const status = document.querySelector('[data-copy-status]');
    if (reviewQuantity && reviewQuantity.value !== reviewQuantity.defaultValue) {
      status.textContent = 'Use Update summary to apply your new quantity before copying.';
      reviewQuantity.form.querySelector('button').focus();
      return;
    }
    try {
      await navigator.clipboard.writeText(message.value);
      status.textContent = 'Order message copied. Paste it into WhatsApp.';
    } catch (error) {
      message.focus(); message.select();
      status.textContent = 'Select and copy the message above using your device’s copy action.';
    }
  });
});
