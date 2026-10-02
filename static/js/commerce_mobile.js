document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('checkoutForm');
  if (!form) return;
  const media = window.matchMedia('(max-width:767px)');
  const steps = Array.from(document.querySelectorAll('[data-checkout-step]'));
  const nav = document.querySelector('.commerce-steps');
  const dock = document.getElementById('mobileCheckoutDock');
  const action = document.getElementById('mobileCheckoutAction');
  const original = document.getElementById('placeOrderBtn');
  const status = document.getElementById('mobileCheckoutStatus');
  const price = document.getElementById('summaryGrandTotal');
  const subtotal = document.getElementById('summarySubtotal');
  const pickup = document.getElementById('shipPickup');
  let step = 0;
  let submitting = false;
  const groups = [['contactSection'], ['shippingSection', 'addressSection'], ['paymentSection'], ['orderSummary']];
  const labels = ['Continue to delivery →', 'Continue to payment →', 'Review your order →', 'Place order'];
  const hints = ['No account needed. You’ll review the full total before placing your order.', 'Choose how to receive your order. Pickup is free.', 'Choose how you prefer to pay.', 'Check your items, delivery, and payment. Place your order when you’re ready.'];

  function sync() {
    document.body.classList.toggle('pickup-mode', pickup.checked);
    document.getElementById('addressSection').hidden = step !== 1 || pickup.checked;
    const quoteReady = form.dataset.quoteState === 'ready';
    const station = document.getElementById('id_pickup_station');
    const contactReview = document.getElementById('checkoutReviewContact');
    if (contactReview) contactReview.textContent = [document.getElementById('id_first_name').value, document.getElementById('id_mobile').value].filter(Boolean).join(' · ');
    document.getElementById('mobileReviewDelivery').textContent = pickup.checked ? 'Pickup · ' + (station?.selectedOptions?.[0]?.textContent || 'Choose a station') : 'Door delivery · ' + [document.getElementById('id_address').value, document.getElementById('id_delivery_city').value].filter(Boolean).join(', ');
    document.getElementById('mobileReviewPayment').textContent = document.getElementById('mobileMoney').checked ? 'Mobile Money · manual payment verification' : 'Pay when you receive or collect your order';
    document.getElementById('mobileCheckoutTotal').textContent = quoteReady ? price.textContent : subtotal.textContent;
    document.getElementById('mobileTotalLabel').textContent = quoteReady ? (pickup.checked ? 'Order total · free pickup' : 'Order total · includes delivery') : 'Items total · delivery next';
    action.textContent = submitting ? 'Placing order…' : labels[step];
    document.querySelector('.commerce-guidance').textContent = 'Step ' + (step + 1) + ' of 4 · ' + hints[step];
    document.querySelector('[data-mobile-back]').setAttribute('aria-label', step > 0 ? 'Back to previous checkout step' : 'Back to cart');
    action.disabled = submitting || (step === 3 && form.dataset.quoteState === 'pending');
    if (step === 3 && original.disabled && !submitting && form.dataset.quoteState !== 'pending') action.textContent = 'Check delivery →';
    if (step === 3 && !quoteReady && !submitting) {
      status.textContent = form.dataset.quoteState === 'pending' ? 'Calculating your delivery total…' : 'Check your delivery location or choose pickup to get an available delivery option.';
    }
  }
  const historyKey = 'jobellCheckoutStep';
  function showStep(value, scroll = true, record = true) {
    if (record && value !== step) window.history.pushState({...window.history.state, [historyKey]: value}, '', window.location.href);
    step = value;
    form.dataset.mobileStep = String(step);
    steps.forEach(button => {
      if (Number(button.dataset.checkoutStep) === step) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
      button.classList.toggle('is-complete', Number(button.dataset.checkoutStep) < step);
    });
    status.textContent = '';
    document.getElementById('checkoutPrevious').hidden = step === 0;
    groups.forEach((ids, index) => ids.forEach(id => {
      document.getElementById(id).hidden = index !== step || (id === 'addressSection' && pickup.checked);
    }));
    sync();
    if (scroll) nav.scrollIntoView({block:'start', behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  }
  function validateStep(index) {
    // Enter can submit without a blur event, so normalize before checking patterns.
    ['id_mobile', 'id_mobile_money_number'].forEach(id => {
      const field = document.getElementById(id);
      if (!field || field.disabled) return;
      let value = field.value.trim().replace(/[\s()-]/g, '');
      if (id === 'id_mobile') {
        if (/^0\d{9}$/.test(value)) value = '+256' + value.slice(1);
        else if (/^256\d{9}$/.test(value)) value = '+' + value;
      } else {
        if (/^\+256\d{9}$/.test(value)) value = '0' + value.slice(4);
        else if (/^256\d{9}$/.test(value)) value = '0' + value.slice(3);
      }
      field.value = value;
    });
    // Mirror the server's conditional requirements without changing submitted data.
    ['id_address', 'id_delivery_region', 'id_delivery_city'].forEach(id => {
      const field = document.getElementById(id);
      if (field) field.required = !pickup.checked && !document.getElementById('id_saved_address')?.value;
    });
    const station = document.getElementById('id_pickup_station');
    if (station) station.required = pickup.checked;
    ['id_mobile_money_number', 'id_payment_evidence'].forEach(id => {
      const field = document.getElementById(id);
      if (field) field.required = document.getElementById('mobileMoney').checked;
    });
    const fields = groups[index].flatMap(id => Array.from(document.getElementById(id)?.querySelectorAll('input,select,textarea') || []));
    const invalid = fields.find(field => !field.disabled && !field.checkValidity());
    if (invalid) {
      showStep(index);
      status.textContent = 'Please check the highlighted field before continuing.';
      const optional = invalid.closest('details');
      if (optional) optional.open = true;
      invalid.reportValidity();
      invalid.focus();
      return false;
    }
    return true;
  }
  function advance() {
    if (submitting) return;
    if (step < 3) {
      if (validateStep(step)) showStep(step + 1);
    } else {
      for (let index = 0; index < 3; index++) if (!validateStep(index)) return;
      if (original.disabled) { showStep(1); status.textContent = 'Check your delivery location or choose an available pickup station.'; return; }
      form.requestSubmit(original);
    }
  }
  action.addEventListener('click', advance);
  document.getElementById('checkoutPrevious').addEventListener('click', () => showStep(Math.max(0, step - 1)));
  form.addEventListener('keydown', function (event) {
    // The desktop submit button may be disabled while delivery is incomplete.
    // Handle the keyboard's Next/Enter action independently on mobile steps.
    if (event.key === 'Enter' && !event.isComposing &&
        event.target.matches('input:not([type="radio"]):not([type="checkbox"])')) {
      event.preventDefault();
      advance();
    }
  });
  document.querySelector('[data-mobile-back]').addEventListener('click', event => {
    if (step > 0) { event.preventDefault(); window.history.back(); }
  });
  steps.forEach(button => button.addEventListener('click', () => {
    const target = Number(button.dataset.checkoutStep);
    for (let index = 0; index < target; index++) if (!validateStep(index)) return;
    showStep(target);
  }));
  document.querySelectorAll('[data-mobile-review],.shopping-summary-link').forEach(link => link.addEventListener('click', event => {
    event.preventDefault();
    for (let index = 0; index < 3; index++) if (!validateStep(index)) return;
    showStep(3);
  }));
  form.addEventListener('submit', function (event) {
    if (step !== 3) { event.preventDefault(); advance(); return; }
    for (let index = 0; index < 3; index++) if (!validateStep(index)) { event.preventDefault(); return; }
    if (submitting || original.disabled) { event.preventDefault(); return; }
    submitting = true;
    sync();
  }, true);
  form.addEventListener('change', sync);
  new MutationObserver(sync).observe(original, {attributes:true, attributeFilter:['disabled']});
  new MutationObserver(sync).observe(price, {childList:true,subtree:true});
  new MutationObserver(sync).observe(form, {attributes:true,attributeFilter:['data-quote-state']});
  function responsive() {
    const main = document.querySelector('.checkout-main');
    const shipping = document.getElementById('shippingSection');
    const address = document.getElementById('addressSection');
    main.insertBefore(shipping, address);
    document.body.classList.add('has-mobile-flow');
    nav.hidden = false;
    dock.hidden = false;
    document.querySelectorAll('.checkout-accordion-toggle').forEach(toggle => {
      toggle.removeAttribute('data-bs-toggle');
      toggle.setAttribute('aria-expanded','true');
    });
    sync();
  }
  media.addEventListener('change', responsive);
  const firstError = document.querySelector('.checkout-error');
  if (firstError) {
    const index = groups.findIndex(ids => ids.some(id => document.getElementById(id)?.contains(firstError)));
    if (index >= 0) step = index;
  }
  const restoredStep = window.history.state?.[historyKey];
  if (!firstError && Number.isInteger(restoredStep) && restoredStep >= 0 && restoredStep <= 3) step = restoredStep;
  window.history.replaceState({...window.history.state, [historyKey]: step}, '', window.location.href);
  window.addEventListener('popstate', event => {
    const previous = event.state?.[historyKey];
    if (Number.isInteger(previous) && previous >= 0 && previous <= 3) showStep(previous, true, false);
  });
  function positionDock() {
    const viewport = window.visualViewport;
    dock.style.bottom = (viewport && media.matches ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop) : 0) + 'px';
  }
  window.visualViewport?.addEventListener('resize', positionDock);
  window.visualViewport?.addEventListener('scroll', positionDock);
  window.addEventListener('resize', positionDock);
  positionDock();
  showStep(step, false, false);
  responsive();
  window.addEventListener('pageshow', function () {
    submitting = false;
    if (original.textContent.includes('Placing order')) {
      original.innerHTML = '<span>Place order</span>';
      original.disabled = form.dataset.quoteState !== 'ready';
    }
    sync();
  });
});
