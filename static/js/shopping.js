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
