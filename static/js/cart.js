document.addEventListener('DOMContentLoaded', function () {
  const forms = Array.from(document.querySelectorAll('.cart-qty-form'));
  forms.forEach(function (form) {
    const input = form.elements.quantity;
    const steps = Array.from(form.querySelectorAll('[data-step]'));
    const status = form.closest('.cart-item').querySelector('.cart-field-status');
    form.querySelector('button[type="submit"]').hidden = true;
    const save = function () {
      if (!form.dataset.pending && input.value !== input.defaultValue) {
        form.requestSubmit();
      }
    };
    const sync = function () {
      steps.forEach(button => { button.disabled = Boolean(form.dataset.pending) || input.disabled || (Number(button.dataset.step) < 0 ? Number(input.value) <= 1 : Number(input.value) >= Number(input.max)); });
      status.textContent = form.dataset.pending ? 'Updating cart…' : (input.value !== input.defaultValue ? 'Quantity changes save automatically when you finish editing.' : '');
    };
    steps.forEach(function (button) {
      button.hidden = false;
      button.addEventListener('click', function () {
        input.value = Math.min(Number(input.max), Math.max(1, (Number(input.value) || 1) + Number(button.dataset.step)));
        sync();
        save();
      });
    });
    input.addEventListener('input', sync);
    input.addEventListener('change', save);
    sync();
  });
  document.querySelectorAll('[data-cart-continue]').forEach(link => link.addEventListener('click', function (event) {
    const dirty = forms.find(form => form.elements.quantity.value !== form.elements.quantity.defaultValue);
    if (dirty) {
      event.preventDefault();
      document.getElementById('cart-action-status').textContent = 'Updating your cart before continuing…';
      dirty.elements.quantity.focus();
      if (!dirty.dataset.pending) dirty.requestSubmit();
    }
  }));
  document.querySelectorAll('.cart-qty-form,.cart-remove-form').forEach(form => {
    form.addEventListener('submit', function (event) {
      if (form.dataset.pending) { event.preventDefault(); return; }
      form.dataset.pending = 'true';
      form.querySelectorAll('[data-step]').forEach(button => { button.disabled = true; });
      if (form.classList.contains('cart-qty-form')) {
        form.closest('.cart-item').querySelector('.cart-field-status').textContent = 'Updating cart…';
      }
      const button = form.querySelector('button[type="submit"]');
      button.dataset.label = button.textContent;
      button.disabled = true;
      button.textContent = form.classList.contains('cart-remove-form') ? 'Removing…' : 'Updating…';
    });
  });
  window.addEventListener('pageshow', function () {
    document.querySelectorAll('form[data-pending]').forEach(form => {
      delete form.dataset.pending;
      const button = form.querySelector('button[type="submit"]');
      button.disabled = false; button.textContent = button.dataset.label;
      if (form.classList.contains('cart-qty-form')) {
        form.elements.quantity.dispatchEvent(new Event('input'));
      }
    });
  });
});
