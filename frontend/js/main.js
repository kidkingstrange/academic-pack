// Countdown Timer
(function() {
  const KEY = 'ac_expiry';
  let expiry = localStorage.getItem(KEY);
  if (!expiry || isNaN(Number(expiry))) {
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
      el.textContent = '0:00:00';
      if (bar) bar.classList.add('urgency-bar--expired');
      
      // Update prices on page if expired
      document.querySelectorAll('.new').forEach(n => n.textContent = '₦5,000');
      document.querySelectorAll('.value-table__row--final .value-table__price').forEach(n => n.textContent = '₦5,000');
      document.querySelectorAll('.final-cta__price strong').forEach(n => n.textContent = '₦5,000');
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
