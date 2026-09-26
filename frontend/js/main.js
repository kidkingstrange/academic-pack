// Countdown Timer & Price Controller
(function() {
  const urlParams = new URLSearchParams(window.location.search);
  const refParam = (urlParams.get('ref') || '').trim();
  const storedRef = (localStorage.getItem('ac_referral_code') || '').trim();
  const isAffiliateRef = !!(refParam || storedRef || urlParams.get('price') === '5000');
  const activeRef = refParam || storedRef || 'PARTNER';

  const bar = document.getElementById('urgency-bar');
  const el = document.getElementById('countdown');

  if (isAffiliateRef) {
    // ── AFFILIATE 48-HOUR URGENCY & PRICE JUMP ENGINE ──────────────────
    const AFF_KEY = 'ac_aff_expiry';
    let affExpiry = localStorage.getItem(AFF_KEY);
    if (!affExpiry || isNaN(Number(affExpiry))) {
      affExpiry = Date.now() + 48 * 60 * 60 * 1000;
      try { localStorage.setItem(AFF_KEY, affExpiry); } catch (e) {}
    }
    affExpiry = Number(affExpiry);

    // Make sure urgency bar is visible and styled for the affiliate offer
    if (bar) {
      bar.style.display = 'block';
      bar.classList.remove('urgency-bar--expired');
    }

    function applyAffiliateActiveState() {
      // Set ₦5,000 partner price across all price displays
      document.querySelectorAll('.price-current').forEach(n => n.textContent = '₦5,000');

      // Update hero ledger for affiliate visitors
      document.querySelectorAll('.ledger__ratio-pill').forEach(pill => {
        pill.innerHTML = `<i class="bi bi-tag-fill"></i> SPECIAL PARTNER RATE: ₦5,000`;
      });
      document.querySelectorAll('.pillar__eyebrow--gold').forEach(el => {
        el.textContent = 'PARTNER ACCESS TODAY';
      });

      // Update price warning notices to highlight the 48-hour lock
      document.querySelectorAll('.price-warning-notice').forEach(notice => {
        notice.style.display = 'block';
        notice.innerHTML = `⚠️ <strong>48-HOUR PARTNER PRICE LOCK:</strong> Your special <strong>₦5,000</strong> partner rate is temporarily reserved through this referral link (Standard Retail Value: <strong>₦20,000</strong>). In 48 hours, this page reverts to the standard <strong>₦20,000</strong> retail price.`;
      });

      // Update discount badges with clean, non-wrapping copy
      document.querySelectorAll('.price-urgency-badge').forEach(badge => {
        badge.style.display = 'inline-block';
        badge.innerHTML = `🔥 <strong>Special Partner Rate</strong> — ₦5,000 Limited Access (75% OFF)`;
      });
      document.querySelectorAll('.showcase__pill-badge, .mobile-price-discount').forEach(badge => {
        badge.innerHTML = `🔥 Partner Rate: ₦5,000 (75% OFF)`;
      });
      document.querySelectorAll('.hero__price-float .discount-badge').forEach(badge => {
        badge.innerHTML = `75% OFF PARTNER SPECIAL`;
      });
      document.querySelectorAll('.value-table__row--final .value-table__label span').forEach(el => {
        el.textContent = 'Your Partner Price Today (75% OFF)';
      });
      document.querySelectorAll('.mid-cta__sub').forEach(el => {
        el.textContent = '7 books. Proven frameworks. Instant delivery. Standard ₦20,000 retail value — claim the complete system today for just ₦5,000.';
      });
    }

    function applyAffiliateExpiredState() {
      if (bar) {
        bar.classList.add('urgency-bar--expired');
        bar.innerHTML = `
          <div class="urgency-bar__expired-notice">
            <span>💡 <strong>Your 48-hour partner access window has expired.</strong> The package has reverted to the standard retail price of <strong>₦20,000</strong>.</span>
          </div>
        `;
      }
      // Update all price displays to full retail ₦20,000
      document.querySelectorAll('.price-current').forEach(n => n.textContent = '₦20,000');
      document.querySelectorAll('.price-urgency-badge').forEach(badge => {
        badge.innerHTML = 'Standard Retail Price (₦20,000)';
      });
      document.querySelectorAll('.showcase__pill-badge, .mobile-price-discount').forEach(badge => {
        badge.innerHTML = 'Standard Price: ₦20,000';
      });
      document.querySelectorAll('.hero__price-float .discount-badge').forEach(badge => {
        badge.innerHTML = 'STANDARD RETAIL VALUE';
      });
      document.querySelectorAll('.value-table__row--final .value-table__label span').forEach(el => {
        el.textContent = 'Standard Retail Price';
      });
      document.querySelectorAll('.price-warning-notice').forEach(notice => {
        notice.style.display = 'block';
        notice.innerHTML = `💡 <strong>Notice:</strong> The 48-hour partner discount has closed. This package is now available at the standard <strong>₦20,000</strong> rate.`;
      });
      document.querySelectorAll('.mid-cta__sub').forEach(el => {
        el.textContent = '7 books. Proven frameworks. Instant delivery. Claim the complete 7-part system today at the standard ₦20,000 retail price.';
      });
      document.querySelectorAll('.hero__price-float .old-price, .mobile-price-old, .mid-cta__old, .mid-cta__arrow').forEach(el => {
        el.style.display = 'none';
      });
      document.querySelectorAll('.aff-badge-countdown').forEach(b => b.textContent = 'Expired');
    }

    let affTimerId = null;
    function tickAffiliate() {
      const diff = affExpiry - Date.now();
      if (diff <= 0) {
        if (affTimerId) { clearInterval(affTimerId); affTimerId = null; }
        applyAffiliateExpiredState();
        return;
      }

      applyAffiliateActiveState();

      const totalSec = Math.floor(diff / 1000);
      const h = Math.floor(totalSec / 3600);
      const m = Math.floor((totalSec % 3600) / 60);
      const s = totalSec % 60;
      const formatted = `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;

      if (el) {
        el.textContent = formatted;
      }
      const textSpan = document.getElementById('urgency-bar-text');
      if (textSpan && bar && !bar.classList.contains('urgency-bar--expired')) {
        textSpan.innerHTML = `🔥 <strong>SPECIAL PARTNER PASS:</strong> ₦5,000 Partner Rate (Standard Retail: ₦20,000) — 48-Hour Lock: <strong id="countdown">${formatted}</strong>`;
      }
      const urgencyCta = bar ? bar.querySelector('.urgency-bar__cta') : null;
      if (urgencyCta && !urgencyCta.dataset.partnerUpdated) {
        urgencyCta.innerHTML = `GET IT NOW — ₦5,000 <i class="bi bi-arrow-right"></i>`;
        urgencyCta.dataset.partnerUpdated = 'true';
      }
      document.querySelectorAll('.aff-badge-countdown').forEach(b => {
        b.textContent = formatted;
      });
    }

    tickAffiliate();
    if (affExpiry - Date.now() > 0) {
      affTimerId = setInterval(tickAffiliate, 1000);
    }
    return;
  }

  // ── DIRECT / ORGANIC 24-HOUR BATCH TIMER ──────────────
  const KEY = 'ac_expiry';
  let expiry = localStorage.getItem(KEY);
  if (!expiry || isNaN(Number(expiry))) {
    expiry = Date.now() + 24 * 60 * 60 * 1000;
    try { localStorage.setItem(KEY, expiry); } catch (e) {}
  }
  expiry = Number(expiry);

  let timerId = null;
  function tick() {
    if (!el) return;
    let diff = expiry - Date.now();
    if (diff <= 0) {
      // Roll over for current batch — preserve ₦2,000 price
      expiry = Date.now() + 24 * 60 * 60 * 1000;
      try { localStorage.setItem(KEY, expiry); } catch (e) {}
      diff = expiry - Date.now();
    }
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    el.textContent = `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  }
  tick();
  timerId = setInterval(tick, 1000);
})();

// Live Real-Time Buyer Counter (Displays ONLY when live sales reach 500+)
(function() {
  const el = document.getElementById('scarcity-num');
  const container = document.getElementById('scarcity-container') || (el ? el.closest('.scarcity') : null);
  if (!el) return;

  async function updateLiveSalesCount() {
    try {
      const res = await fetch('/api/public/sales-count');
      const data = await res.json();
      if (data && typeof data.sales_count === 'number') {
        const count = data.sales_count;
        el.textContent = count;
        // Only show live buyer counter once total verified sales reach 500+
        if (container) {
          container.style.display = (count >= 500) ? 'flex' : 'none';
        }
      }
    } catch (e) {
      /* ignore transient network errors */
    }
  }

  updateLiveSalesCount();
  // Refresh live count every 30 seconds
  setInterval(updateLiveSalesCount, 30000);
})();
