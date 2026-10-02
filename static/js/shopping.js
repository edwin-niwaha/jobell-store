document.addEventListener('DOMContentLoaded', function () {
  // Keep the selected variant price visible alongside its purchase action.
  document.querySelectorAll('.js-add-to-cart-form select[name="volume_id"]').forEach(function (select) {
    const card = select.closest('article');
    const price = card?.querySelector('.platform-product-price, [data-variant-price]');
    if (!price) return;
    price.setAttribute('aria-live', 'polite');
    function updatePrice() {
      const option = select.selectedOptions[0];
      const amount = option?.textContent.match(/UGX\s+([\d,]+(?:\.\d+)?)/);
      if (amount) price.textContent = 'UGX ' + amount[1];
    }
    select.addEventListener('change', updatePrice);
    updatePrice();
  });
  // A fixed header must account for wrapped navigation at every viewport width.
  const nav = document.querySelector('.platform-store-nav');
  if (nav && window.ResizeObserver) {
    new ResizeObserver(function () {
      document.body.style.paddingTop = (nav.getBoundingClientRect().height + 12) + 'px';
      document.documentElement.style.setProperty('--store-nav-height', (nav.getBoundingClientRect().height + 24) + 'px');
    }).observe(nav);
  }
  window.addEventListener('load', function () {
    if (window.location.hash === '#platform-categories') document.getElementById('platform-categories')?.scrollIntoView({block:'start'});
  });
});

// Add from product cards without navigating away or losing the selected volume.
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.platform-product-card .js-add-to-cart-form, .product-card .js-add-to-cart-form').forEach(function (form) {
    const button = form.querySelector('[data-cart-submit]');
    if (!button) return;
    const status = document.createElement('span');
    status.className = 'shopping-cart-feedback';
    status.setAttribute('role', 'status');
    form.appendChild(status);
    form.addEventListener('submit', async function (event) {
      event.preventDefault();
      if (button.disabled || !form.reportValidity()) return;
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      status.textContent = 'Adding…';
      try {
        const response = await fetch(form.action, {
          method: 'POST', body: new FormData(form), credentials: 'same-origin',
          headers: {'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'}
        });
        const result = await response.json();
        status.textContent = result.message || (response.ok ? 'Added to cart.' : 'Could not add this option.');
        if (result.cart_count !== undefined) {
          document.querySelectorAll('[data-cart-count]').forEach(function (badge) { badge.textContent = result.cart_count; });
        }
      } catch (error) {
        status.textContent = 'Unable to confirm. Check your cart before trying again.';
      } finally {
        button.disabled = false;
        button.removeAttribute('aria-busy');
      }
    });
  });
});

// Share each card's chosen volume with the existing WhatsApp order summary.
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.shopping-whatsapp-form').forEach(function (form) {
    const purchase = form.closest('article')?.querySelector('.js-add-to-cart-form');
    const volume = purchase?.querySelector('[name="volume_id"]');
    const quantity = purchase?.querySelector('[name="quantity"]');
    const button = form.querySelector('button');
    function sync() {
      form.elements.volume_id.value = volume?.value || '';
      form.elements.quantity.value = quantity?.value || '1';
      button.disabled = !volume?.value;
    }
    volume?.addEventListener('change', sync);
    quantity?.addEventListener('input', sync);
    form.addEventListener('submit', function (event) {
      sync();
      if (!volume?.value || !purchase.reportValidity()) event.preventDefault();
    });
    sync();
  });
});
