(() => {
  const body = document.body;
  const menu = document.getElementById('menuButton');
  const overlay = document.getElementById('sidebarOverlay');
  const close = () => body.classList.remove('sidebar-open');
  if (menu) menu.addEventListener('click', () => body.classList.toggle('sidebar-open'));
  if (overlay) overlay.addEventListener('click', close);
  document.querySelectorAll('.side-link').forEach(link => link.addEventListener('click', close));

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => navigator.serviceWorker.register('/static/service-worker.js').catch(() => {}));
  }

  const updateNetwork = () => {
    document.querySelectorAll('[data-network-state]').forEach(el => {
      el.textContent = navigator.onLine ? 'Online' : 'Offline';
      el.classList.toggle('offline', !navigator.onLine);
    });
  };
  window.addEventListener('online', updateNetwork);
  window.addEventListener('offline', updateNetwork);
  updateNetwork();
})();
