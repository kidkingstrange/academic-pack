// Countdown Timer & Price Controller
(function() {
  const KEY = 'ac_expiry';
  let expiry = localStorage.getItem(KEY);
  const urlParams = new URLSearchParams(window.location.search);
  const isAffiliateRef = urlParams.has('ref') || urlParams.get('price') === '5000';

  if (isAffiliateRef) {
    expiry = Date.now() - 1000;
    localStorage.setItem(KEY, expiry);
  } else if (!expiry || isNaN(Number(expiry))) {
    expiry = Date.now() + 24 * 60 * 60 * 1000;
    localStorage.setItem(KEY, expiry);
  }
  expiry = Number(expiry);
  const el = document.getElementById('countdown');
  const bar = document.getElementById('urgency-bar');

  function tick() {
    if (!el) return;
    const diff = expiry - Date.now();
    if (diff <= 0) {
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
    requestAnimationFrame(tick);
  }
  tick();
})();

// Scarcity Counter
(function() {
  const el = document.getElementById('scarcity-num');
  if (!el) return;
  let count = Math.floor(Math.random() * 8) + 14; 
  el.textContent = count;
  
  function schedule() {
    const delay = (Math.random() * 3 + 6) * 60 * 1000;
    setTimeout(() => {
      count++;
      el.textContent = count;
      schedule();
    }, delay);
  }
  schedule();
})();
