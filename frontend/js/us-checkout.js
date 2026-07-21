// Dedicated US Checkout & Urgency Script — Brand Theme Compatible
(function() {
  const API_BASE = '/api';
  const EXPIRY_KEY = 'us_ac_expiry';
  const PURCHASED_KEY = 'us_ac_purchased';

  // ── 24-Hour Urgency Countdown Timer ──────────────────────────────────────────
  function initCountdown() {
    let expiry = localStorage.getItem(EXPIRY_KEY);
    if (!expiry) {
      expiry = Date.now() + 24 * 60 * 60 * 1000; // 24 hours from first visit
      localStorage.setItem(EXPIRY_KEY, expiry);
    } else {
      expiry = Number(expiry);
    }

    const timerEl = document.getElementById('us-countdown') || document.getElementById('countdown');
    const update = () => {
      const remaining = expiry - Date.now();
      if (remaining <= 0) {
        if (timerEl) timerEl.textContent = "00:00:00 (Price Expired)";
        // Update price displays to late price $30
        document.querySelectorAll('.us-price-current, .price-current').forEach(el => el.textContent = '$30');
        document.querySelectorAll('.us-price-savings').forEach(el => el.textContent = '(Save $142)');
        return;
      }

      const hrs = String(Math.floor(remaining / 3600000)).padStart(2, '0');
      const mins = String(Math.floor((remaining % 3600000) / 60000)).padStart(2, '0');
      const secs = String(Math.floor((remaining % 60000) / 1000)).padStart(2, '0');

      if (timerEl) timerEl.textContent = `${hrs}:${mins}:${secs}`;
    };

    update();
    setInterval(update, 1000);
  }

  // ── Modal State Control ──────────────────────────────────────────────────────
  window.openCheckout = window.openUSCheckout = function() {
    if (localStorage.getItem('ac_purchased') === 'true' || localStorage.getItem(PURCHASED_KEY) === 'true') {
      window.location.href = '/library';
      return;
    }
    const modal = document.getElementById('us-checkout-modal') || document.getElementById('checkout-modal');
    if (modal) {
      modal.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  };

  window.closeCheckout = window.closeUSCheckout = function() {
    const modal = document.getElementById('us-checkout-modal') || document.getElementById('checkout-modal');
    if (modal) {
      modal.classList.remove('open');
      document.body.style.overflow = '';
    }
  };

  // ── Returning Customer CTA Swap ──────────────────────────────────────────────
  function checkReturningCustomer() {
    if (localStorage.getItem('ac_purchased') === 'true' || localStorage.getItem(PURCHASED_KEY) === 'true') {
      document.querySelectorAll('.btn--mega, .nav__cta, .urgency-bar__cta, .sticky-cta-bar__btn').forEach(btn => {
        btn.innerHTML = 'Access Your Library <i class="bi bi-arrow-right"></i>';
        btn.onclick = function(e) {
          e.preventDefault();
          window.location.href = '/library';
        };
      });
    }
  }

  // ── Lead Form & Payment Initialization ────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    initCountdown();
    checkReturningCustomer();

    const form = document.getElementById('us-checkout-form') || document.getElementById('lead-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const nameInput = document.getElementById('us-name') || document.getElementById('name');
      const emailInput = document.getElementById('us-email') || document.getElementById('email');
      const btn = document.getElementById('us-submit-btn') || document.getElementById('submit-lead');
      const errorEl = document.getElementById('us-checkout-error') || document.getElementById('payment-error');

      const name = nameInput ? nameInput.value.trim() : '';
      const email = emailInput ? emailInput.value.trim().toLowerCase() : '';
      if (!name || !email) return;

      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Initializing Secure Checkout...';
      }
      if (errorEl) errorEl.style.display = 'none';

      try {
        const clientExpiry = localStorage.getItem(EXPIRY_KEY);
        const ref = new URLSearchParams(window.location.search).get('ref');

        const res = await fetch(`${API_BASE}/payments/initialize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: name,
            email: email,
            client_expiry: clientExpiry ? Number(clientExpiry) : null,
            country: 'US',
            currency: 'USD',
            payment_method: 'card',
            referral_code: ref || null,
          }),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Failed to initialize payment');
        }

        if (data.redirect_url) {
          window.location.href = data.redirect_url;
        } else {
          throw new Error('No redirect URL returned from gateway');
        }
      } catch (err) {
        if (errorEl) {
          errorEl.textContent = err.message || 'Payment processing error. Please try again.';
          errorEl.style.display = 'block';
        }
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = 'Complete Instant Access — <span class="price-current">$15</span> <i class="bi bi-arrow-right"></i>';
        }
      }
    });
  });
})();
