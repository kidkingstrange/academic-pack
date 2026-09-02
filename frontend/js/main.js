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

    // Set initial ₦5,000 price (75% OFF ₦20,000 retail)
    document.querySelectorAll('.price-current').forEach(n => n.textContent = '₦5,000');

    // Update price warning notices to highlight the 48-hour lock
    document.querySelectorAll('.price-warning-notice').forEach(notice => {
      notice.style.display = 'block';
      notice.innerHTML = `⚠️ <strong>48-HOUR PARTNER PRICE LOCK:</strong> Your special <strong>₦5,000</strong> student rate (75% OFF) is temporarily reserved through this referral link. In 48 hours, this page automatically reverts to the standard <strong>₦20,000</strong> retail price.`;
    });

    // Update discount badges
    document.querySelectorAll('.price-urgency-badge').forEach(badge => {
      badge.style.display = 'inline-block';
      badge.innerHTML = `🔥 <strong>75% Partner Discount</strong> — Price jumps to ₦20,000 in <span class="aff-badge-countdown">48:00:00</span>`;
    });

    let affTimerId = null;
    function tickAffiliate() {
      const diff = affExpiry - Date.now();
      if (diff <= 0) {
        if (affTimerId) { clearInterval(affTimerId); affTimerId = null; }
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
        document.querySelectorAll('.price-warning-notice').forEach(notice => {
          notice.innerHTML = `💡 <strong>Notice:</strong> The 48-hour partner discount has closed. This package is now available at the standard <strong>₦20,000</strong> rate.`;
        });
        document.querySelectorAll('.aff-badge-countdown').forEach(b => b.textContent = 'Expired');
        return;
      }

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
        textSpan.innerHTML = `🔥 <strong>SPECIAL PARTNER PASS:</strong> 75% OFF (₦5,000) — Price Jumps to ₦20,000 In: <strong id="countdown">${formatted}</strong>`;
      }
      document.querySelectorAll('.aff-badge-countdown').forEach(b => {
        b.textContent = formatted;
      });
    }

    tickAffiliate();
    affTimerId = setInterval(tickAffiliate, 1000);
    return;
  }

  // ── DIRECT / ORGANIC 24-HOUR EARLY BIRD FLOW (UNCHANGED) ──────────────
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
    const diff = expiry - Date.now();
    if (diff <= 0) {
      if (timerId) { clearInterval(timerId); timerId = null; }
      if (bar) {
        bar.classList.add('urgency-bar--expired');
        if (!bar.querySelector('.urgency-bar__expired-notice')) {
          bar.innerHTML = `
            <div class="urgency-bar__expired-notice">
              <span>💡 <strong>Your 24-hour early-bird window has ended.</strong> The package is now available at the standard price of <strong>₦5,000</strong>. Thank you for your understanding — the full value of all 7 books is still yours the moment you order.</span>
            </div>
          `;
        }
      }
      
      // Update all current price displays to standard price
      document.querySelectorAll('.price-current').forEach(n => n.textContent = '₦5,000');
      
      // Update all discount badges and labels from 90% to 75%
      document.querySelectorAll('.price-urgency-badge').forEach(n => {
        if (n.textContent.includes('window is closing')) {
          n.innerHTML = 'The 90% discount window has closed.';
        } else {
          n.innerHTML = n.innerHTML.replace(/90%/g, '75%');
        }
      });
      return;
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
