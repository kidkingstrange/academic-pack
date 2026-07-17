// Countdown Timer & Price Controller
(function() {
  const KEY = 'ac_expiry';
  const urlParams = new URLSearchParams(window.location.search);
  const isAffiliateRef = urlParams.has('ref') || urlParams.get('price') === '5000';

  if (isAffiliateRef) {
    // Hide urgency bar and 24-hour warning text for affiliate referral links
    const bar = document.getElementById('urgency-bar');
    if (bar) bar.style.display = 'none';

    document.querySelectorAll('.price-warning-notice').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.price-current').forEach(n => n.textContent = '₦5,000');
    document.querySelectorAll('.price-urgency-badge').forEach(n => {
      n.style.display = 'none';
    });
    return;
  }

  let expiry = localStorage.getItem(KEY);
  if (!expiry || isNaN(Number(expiry))) {
    expiry = Date.now() + 24 * 60 * 60 * 1000;
    localStorage.setItem(KEY, expiry);
  }
  expiry = Number(expiry);
  const el = document.getElementById('countdown');
  const bar = document.getElementById('urgency-bar');

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
