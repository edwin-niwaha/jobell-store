document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.account-field').forEach(function (group) {
    const input = group.querySelector('input,select,textarea');
    if (!input) return;
    const descriptions = Array.from(group.querySelectorAll('.account-help,.account-error')).map(node => node.id).filter(Boolean);
    if (descriptions.length) input.setAttribute('aria-describedby', descriptions.join(' '));
    if (group.classList.contains('has-error')) input.setAttribute('aria-invalid', 'true');
    if (input.type !== 'password') return;
    const wrapper = document.createElement('div');
    wrapper.className = 'account-password';
    input.before(wrapper);
    wrapper.appendChild(input);
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.textContent = 'Show';
    toggle.setAttribute('aria-label', 'Show ' + (group.querySelector('label')?.textContent || 'password'));
    toggle.setAttribute('aria-controls', input.id);
    toggle.setAttribute('aria-pressed', 'false');
    wrapper.appendChild(toggle);
    toggle.addEventListener('click', function () {
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      toggle.textContent = visible ? 'Hide' : 'Show';
      toggle.setAttribute('aria-pressed', String(visible));
      toggle.setAttribute('aria-label', (visible ? 'Hide ' : 'Show ') + (group.querySelector('label')?.textContent || 'password'));
    });
  });
  const firstError = document.querySelector('.account-field.has-error input,.account-field.has-error textarea');
  if (firstError) firstError.focus();
  document.querySelectorAll('.account-form').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (event.defaultPrevented) return;
      if (form.dataset.pending === 'true') { event.preventDefault(); return; }
      const button = form.querySelector('button[type="submit"]');
      if (!button) return;
      form.dataset.pending = 'true';
      button.dataset.originalText = button.textContent;
      button.disabled = true;
      button.textContent = 'Please wait…';
    });
  });
  window.addEventListener('pageshow', function () {
    document.querySelectorAll('.account-form').forEach(function (form) {
      delete form.dataset.pending;
      const button = form.querySelector('button[type="submit"]');
      if (button?.dataset.originalText) { button.disabled = false; button.textContent = button.dataset.originalText; }
    });
  });
});
