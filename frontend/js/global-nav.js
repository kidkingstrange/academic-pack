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

    // Ensure affiliate registration link exists across every page
    ensureAffiliateLinks();

    // Ensure universal affiliate registration modal script is loaded
    ensureAffiliateModalScript();
  }

  function ensureAffiliateModalScript() {
    if (window.openAffiliateRegisterModal) return;
    if (document.querySelector('script[src*="affiliate-modal.js"]')) return;
    var script = document.createElement('script');
    script.src = '/js/affiliate-modal.js';
    script.defer = true;
    document.head.appendChild(script);
  }

  // ── Universal Affiliate Links Injection ──────────────────────────────────
  function ensureAffiliateLinks() {
    var regHref = '/affiliate-register.html';

    // 0. Safety Cleanup: Brand elements must strictly contain only brand text/logo
    var brandEls = document.querySelectorAll('.footer__brand, .nav__brand, .global-brand, .blog-footer__brand');
    brandEls.forEach(function(b) {
      var rogue = b.querySelectorAll('a[href*="affiliate"], a[href*="affiliates"]');
      rogue.forEach(function(r) { r.remove(); });
    });

    // 1. Footers across all page layouts (target only link rows, never brand headers)
    var footers = document.querySelectorAll('.site-footer .footer-links, .blog-footer__links, .footer-links, .footer__links');
    footers.forEach(function(f) {
      if (f.classList.contains('footer__brand') || f.closest('.footer__brand') || f.classList.contains('nav__brand')) return;
      var parentFooter = f.closest('footer');
      if (parentFooter && parentFooter.querySelector('a[href*="affiliate-register"]')) return;
      if (f.querySelectorAll && !f.querySelector('a[href*="affiliate-register"]')) {
        var a = document.createElement('a');
        a.href = regHref;
        a.textContent = 'Become an Affiliate';
        var amb = f.querySelector('a[href*="affiliate/dashboard"]');
        if (amb) {
          f.insertBefore(a, amb);
        } else {
          f.appendChild(a);
        }
      }
    });

    // 2. Mobile Drawer Navigation
    var drawerGroups = document.querySelectorAll('.drawer-nav-group');
    drawerGroups.forEach(function(group) {
      var title = group.querySelector('.drawer-group-title');
      if (title && (title.textContent.indexOf('BUYER') !== -1 || title.textContent.indexOf('EXPLORE') !== -1)) {
        if (!group.querySelector('a[href*="affiliate-register"]')) {
          var a = document.createElement('a');
          a.href = regHref;
          a.className = 'drawer-nav-item';
          a.onclick = closeDrawer;
          a.innerHTML = '<i class="bi bi-gift-fill" style="color:var(--gold,#f59e0b)"></i> <span>Become an Affiliate (Earn 60%)</span>';
          var amb = group.querySelector('a[href*="affiliate/dashboard"]');
          if (amb) {
            group.insertBefore(a, amb);
          } else {
            group.appendChild(a);
          }
        }
      }
    });

    // 3. Desktop Navigation Header
    var navs = document.querySelectorAll('.global-nav');
    navs.forEach(function(nav) {
      if (!nav.querySelector('a[href*="affiliate-register"]')) {
        var a = document.createElement('a');
        a.href = regHref;
        a.className = 'global-nav__link';
        a.textContent = 'Affiliates';
        var cta = nav.querySelector('.global-nav__cta-pill') || nav.querySelector('.reader-auth-btn');
        if (cta) {
          nav.insertBefore(a, cta);
        } else {
          nav.appendChild(a);
        }
      }
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
