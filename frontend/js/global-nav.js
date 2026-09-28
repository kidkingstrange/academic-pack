/**
 * Global Site Navigation & Mobile Drawer Controller
 * Shared across Homepage, Academic Comeback Package, Library, and Blog pages.
 */
(function() {
  function openDrawer() {
    var backdrop = document.getElementById('global-drawer-backdrop');
    var drawer = document.getElementById('global-drawer');
    if (backdrop && drawer) {
      backdrop.classList.add('is-open');
      drawer.classList.add('is-open');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeDrawer() {
    var backdrop = document.getElementById('global-drawer-backdrop');
    var drawer = document.getElementById('global-drawer');
    if (backdrop && drawer) {
      backdrop.classList.remove('is-open');
      drawer.classList.remove('is-open');
      document.body.style.overflow = '';
    }
  }

  // Expose to window for inline onclick handlers
  window.openGlobalDrawer = openDrawer;
  window.closeGlobalDrawer = closeDrawer;

  window.openSupportModalFromDrawer = function() {
    closeDrawer();
    if (typeof openRefundModal === 'function') {
      openRefundModal();
    } else {
      window.location.href = '/?support=true';
    }
  };

  // Keyboard and click outside listeners
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeDrawer();
  });

  // Auto-detect ?support=true query parameter on pages with refund modal
  document.addEventListener('DOMContentLoaded', function() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('support') === 'true' && typeof openRefundModal === 'function') {
      setTimeout(function() {
        openRefundModal();
      }, 300);
    }
  });
})();
