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

  // ── Universal Light / Dark Theme Controller (Desktop & Mobile) ──────────
  function updateAllThemeToggles(theme) {
    var isDark = theme === 'dark';
    var btns = document.querySelectorAll('.theme-toggle');
    btns.forEach(function(btn) {
      btn.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
      btn.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
      var text = btn.querySelector('.theme-toggle__text');
      if (text) text.textContent = isDark ? 'Light' : 'Dark';
      var label = btn.querySelector('.theme-toggle__label');
      if (label) label.textContent = isDark ? 'Dark Mode' : 'Light Mode';
    });
  }

  function toggleGlobalTheme(e) {
    if (e) {
      if (typeof e.preventDefault === 'function') e.preventDefault();
      if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try {
      localStorage.setItem('academic_blog_theme', next);
    } catch(err) {}
    updateAllThemeToggles(next);
  }

  window.toggleGlobalTheme = toggleGlobalTheme;

  function initGlobalTheme() {
    var saved = null;
    try {
      saved = localStorage.getItem('academic_blog_theme');
    } catch(err) {}
    var preferred = saved === 'dark' ? 'dark' : 'light';
    
    // Ensure document has attribute set
    var current = document.documentElement.getAttribute('data-theme');
    if (!current) {
      document.documentElement.setAttribute('data-theme', preferred);
      current = preferred;
    }
    updateAllThemeToggles(current);

    // Bind event listeners to every .theme-toggle button in DOM (both desktop & mobile)
    var btns = document.querySelectorAll('.theme-toggle');
    btns.forEach(function(btn) {
      btn.onclick = toggleGlobalTheme;
    });
  }

  // Bind on DOM ready and immediately if document is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGlobalTheme);
  } else {
    initGlobalTheme();
  }

  // Also listen for OS system preference changes if user hasn't explicitly chosen
  if (window.matchMedia) {
    try {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        try {
          if (!localStorage.getItem('academic_blog_theme')) {
            var newTheme = e.matches ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', newTheme);
            updateAllThemeToggles(newTheme);
          }
        } catch(err) {}
      });
    } catch(err) {}
  }
})();
