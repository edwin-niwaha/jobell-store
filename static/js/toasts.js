(() => {
  if (window.JobellToast) { window.JobellToast.init(); return; }
  const titles = { success: 'Success', error: 'Something went wrong', warning: 'Please check', info: 'Update' };
  function init() {
    const hosts = [...document.querySelectorAll('.jobell-toast-host')];
    const host = hosts[0];
    if (!host) return;
    if (host.parentNode !== document.body) document.body.appendChild(host);
    hosts.slice(1).forEach(extra => {
      extra.querySelectorAll('.jobell-toast').forEach(toast => host.appendChild(toast));
      extra.remove();
    });
    host.querySelectorAll('.jobell-toast:not([data-ready])').forEach(element => {
      element.dataset.ready = 'true';
      let remaining = element.dataset.kind === 'error' ? 8000 : 5000;
      let timer, started, dismissed = false;
      const pauses = new Set();
      const progress = element.querySelector('.jobell-toast-progress');
      const dismiss = () => {
        if (dismissed) return;
        dismissed = true;
        clearTimeout(timer);
        element.remove();
      };
      const resume = () => {
        if (dismissed || pauses.size) return;
        started = Date.now();
        if (progress) progress.style.animationPlayState = 'running';
        timer = setTimeout(dismiss, remaining);
      };
      const pause = reason => {
        if (!pauses.size) {
          clearTimeout(timer);
          remaining = Math.max(0, remaining - (Date.now() - started));
        }
        pauses.add(reason);
        if (progress) progress.style.animationPlayState = 'paused';
      };
      const unpause = reason => { pauses.delete(reason); resume(); };
      element.addEventListener('mouseenter', () => pause('hover'));
      element.addEventListener('mouseleave', () => unpause('hover'));
      element.addEventListener('focusin', () => pause('focus'));
      element.addEventListener('focusout', event => {
        if (!element.contains(event.relatedTarget)) unpause('focus');
      });
      const close = element.querySelector('.btn-close');
      if (close) {
        close.removeAttribute('data-bs-dismiss');
        close.removeAttribute('data-dismiss');
        close.textContent = '\u00d7';
        close.addEventListener('click', dismiss);
      }
      element.classList.add('show');
      resume();
    });
  }
  function show(message, kind = 'success') {
    if (!message) return;
    if (!Object.prototype.hasOwnProperty.call(titles, kind)) kind = 'info';
    let host = document.querySelector('.jobell-toast-host');
    if (!host) { host = document.createElement('div'); host.className = 'toast-container jobell-toast-host'; document.body.appendChild(host); }
    const element = document.createElement('div');
    element.className = 'toast jobell-toast';
    element.dataset.kind = kind;
    element.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    element.setAttribute('aria-atomic', 'true');
    element.innerHTML = '<div class="toast-header"><span class="jobell-toast-icon" aria-hidden="true"></span><strong class="me-auto"></strong><button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Dismiss notification"></button></div><div class="toast-body"></div><span class="jobell-toast-progress" aria-hidden="true"></span>';
    element.querySelector('strong').textContent = titles[kind];
    element.querySelector('.toast-body').textContent = String(message);
    host.appendChild(element);
    init();
  }
  window.JobellToast = { init, show };
  document.addEventListener('showMessage', event => { const data = event.detail || {}; show(data.message || data.value, data.kind || 'success'); });
  document.addEventListener('htmx:afterSwap', init);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
