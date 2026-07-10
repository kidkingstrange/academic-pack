// Checkout Logic — Flutterwave V4 Dual Payment Methods
// Bank Transfer (virtual account) + Pay with Bank (Mono redirect)
const API_BASE = '/api';

const modal = document.getElementById('checkout-modal');
const form  = document.getElementById('lead-form');
let userEmail         = '';
let userName          = '';
let currentChargeId   = null;
let currentReference  = null;
let currentVaId       = null;
let currentPayMethod  = 'bank_transfer';
let pollingTimer      = null;
let pollStartedAt     = null;

// ── Pending payment persistence ───────────────────────────────────────────────
// Survives tab close / navigation, so a customer who transfers the money and
// then closes the tab (or comes back later) can still resume verification
// instead of losing the reference and never getting their welcome email.
const PENDING_KEY = 'ac_pending_payment';

function savePendingPayment(bankDetails) {
  try {
    localStorage.setItem(PENDING_KEY, JSON.stringify({
      email: userEmail,
      name: userName,
      charge_id: currentChargeId,
      reference: currentReference,
      va_id: currentVaId,
      payment_method: currentPayMethod,
      bank_details: bankDetails,
      saved_at: Date.now(),
    }));
  } catch (err) { /* localStorage unavailable — non-fatal */ }
}

function clearPendingPayment() {
  try { localStorage.removeItem(PENDING_KEY); } catch (err) { /* ignore */ }
}

function loadPendingPayment() {
  try {
    const raw = localStorage.getItem(PENDING_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (err) {
    return null;
  }
}

function openCheckout() {
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeCheckout() {
  modal.classList.remove('open');
  document.body.style.overflow = '';
  if (pollingTimer) { clearTimeout(pollingTimer); pollingTimer = null; }
}

function showStep(step) {
  document.querySelectorAll('.modal__step').forEach(el => el.classList.remove('active'));
  document.getElementById('step' + step).classList.add('active');
}

function resetCheckout() {
  showStep(1);
  hideBankDetails();
  document.getElementById('payment-spinner').style.display = 'block';
  document.getElementById('payment-error').style.display = 'none';
  document.getElementById('payment-success').style.display = 'none';
}

function hideBankDetails() {
  const bd = document.getElementById('bank-details');
  if (bd) bd.style.display = 'none';
}

function showPaymentError(msg) {
  document.getElementById('payment-spinner').style.display = 'none';
  hideBankDetails();
  document.getElementById('payment-error').style.display = 'block';
  document.getElementById('payment-error-msg').textContent = msg || 'Something went wrong. Please try again.';
}

// ── Payment method selector toggle ────────────────────────────────────────────
document.querySelectorAll('.payment-method-option input[type="radio"]').forEach(radio => {
  radio.addEventListener('change', () => {
    document.querySelectorAll('.payment-method-option').forEach(opt => opt.classList.remove('selected'));
    radio.closest('.payment-method-option').classList.add('selected');
    currentPayMethod = radio.value;
  });
});

// ── Step 1: Submit lead form → initialize payment ─────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const nameInput  = document.getElementById('name');
  const emailInput = document.getElementById('email');
  const btn        = document.getElementById('submit-lead');

  userName  = nameInput.value.trim();
  userEmail = emailInput.value.trim();

  // Read selected payment method
  const pmRadio = document.querySelector('input[name="payment_method"]:checked');
  currentPayMethod = pmRadio ? pmRadio.value : 'bank_transfer';

  btn.disabled   = true;
  btn.innerHTML  = '<span class="spinner-border spinner-border-sm"></span> Processing...';

  try {
    const clientExpiry = localStorage.getItem('ac_expiry');
    const referralCode = localStorage.getItem('ac_referral_code');
    const res = await fetch(`${API_BASE}/payments/initialize`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        name:           userName,
        email:          userEmail,
        client_expiry:  clientExpiry ? Number(clientExpiry) : null,
        payment_method: currentPayMethod,
        referral_code:  referralCode || null,
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Initialization failed');

    currentChargeId  = data.charge_id || null;
    currentReference = data.reference;
    currentVaId      = data.va_id || null;

    showStep(2);
    document.getElementById('payment-spinner').style.display = 'none';

    if (data.action === 'redirect') {
      // 3DS / hosted page — just redirect
      window.location.href = data.redirect_url;
      return;
    }

    if (data.action === 'virtual_account') {
      // Bank Transfer — show virtual account with fee-inclusive amount
      const bankDetails = {
        account_number: data.account_number,
        bank_name:      data.bank_name,
        amount:         data.amount_with_fee || data.amount,
        base_amount:    data.amount,
        expiry:         data.expiry,
        note:           data.note,
      };
      showBankDetails(bankDetails);
      savePendingPayment(bankDetails);
      return;
    }

    // Legacy bank_transfer from charge flow
    showBankDetails(data);
    savePendingPayment(data);

  } catch (err) {
    alert(err.message);
    btn.disabled  = false;
    btn.innerHTML = 'Continue to Payment <i class="bi bi-arrow-right"></i>';
  }
});

// ── Show virtual account details ──────────────────────────────────────────────
function showBankDetails(data) {
  let bd = document.getElementById('bank-details');

  // Create bank-details panel if it doesn't exist yet
  if (!bd) {
    bd = document.createElement('div');
    bd.id        = 'bank-details';
    bd.className = 'bank-details-panel';
    const step2 = document.getElementById('step2');
    step2.appendChild(bd);
  }

  const transferAmount = Number(data.amount);
  const fmt = '₦' + transferAmount.toLocaleString();

  // Calculate fee display if base amount is different
  let feeNote = '';
  if (data.base_amount && data.base_amount !== transferAmount) {
    const fee = transferAmount - data.base_amount;
    feeNote = `<p class="bank-details-fee">Includes ₦${fee.toLocaleString()} processing fee</p>`;
  }

  // Expiry display
  let expiryNote = '';
  if (data.expiry) {
    const expiryDate = new Date(data.expiry);
    const now = new Date();
    const minsLeft = Math.max(0, Math.round((expiryDate - now) / 60000));
    expiryNote = `<p class="bank-details-expiry">⏱ Account expires in ${minsLeft} minute${minsLeft !== 1 ? 's' : ''}</p>`;
  }

  bd.innerHTML = `
    <div class="bank-details-card">
      <p class="bank-details-title">Transfer exactly <strong>${fmt}</strong> to:</p>
      ${feeNote}
      <div class="bank-detail-row">
        <span class="bank-detail-label">Bank</span>
        <strong class="bank-detail-value">${data.bank_name || '—'}</strong>
      </div>
      <div class="bank-detail-row">
        <span class="bank-detail-label">Account Number</span>
        <div style="display: flex; align-items: center; gap: 8px; position: relative;">
          <strong class="bank-detail-value acct-number">${data.account_number || '—'}</strong>
          <button class="copy-btn" onclick="event.stopPropagation(); copyAccountNumber('${data.account_number}', this)" title="Copy Account Number" style="background: none; border: none; padding: 4px; cursor: pointer; display: flex; align-items: center; color: var(--gold-l); font-size: 1.1rem; transition: color 0.2s; outline: none;">
            <i class="bi bi-copy"></i>
          </button>
        </div>
      </div>
      <div class="bank-detail-row">
        <span class="bank-detail-label">Amount</span>
        <strong class="bank-detail-value gold">${fmt}</strong>
      </div>
      ${expiryNote}
      <p class="bank-details-note">${data.note || 'Account is valid for 60 minutes. Transfer the exact amount.'}</p>
      <div id="poll-checking" style="display:none" class="poll-checking">
        <div class="poll-checking__status-row">
          <div class="mini-spinner"></div>
          <span id="poll-status-text">Checking for your payment...</span>
        </div>
        <p class="poll-checking__warning">⚠️ Please don't close this tab or refresh — we're confirming your payment and preparing your library.</p>
        <p class="poll-checking__tip">📧 Once confirmed, check your inbox — and your spam/junk folder too, just in case — for an email from The Scale Conference (thescaleconference.com).</p>
      </div>
      <button class="btn btn-primary btn-check-payment" id="btn-check-payment" onclick="startPolling()">
        I have made the transfer ✓
      </button>
    </div>`;
  bd.style.display = 'block';
}

// ── Polling — tiered intervals for up to ~60 minutes (matches VA expiry) ─────
// This is a convenience for instant feedback only. The webhook is the real
// source of truth for granting access/sending the welcome email — see
// process_webhook_payment() on the backend — so even if a customer closes the
// tab mid-poll, their access isn't lost; the webhook completes it server-side.
const POLL_MAX_ELAPSED_MS = 60 * 60 * 1000; // 60 minutes, matches VA expiry

function pollDelayFor(elapsedMs) {
  if (elapsedMs < 3 * 60 * 1000)  return 5000;  // first 3 min:  every 5s
  if (elapsedMs < 20 * 60 * 1000) return 30000; // next 17 min:  every 30s
  return 60000;                                 // remainder:    every 60s
}

// ── Rotating status messages — purely cosmetic, reduces perceived wait ──────
const POLL_STATUS_MESSAGES = [
  "Confirming your transfer...",
  "Unlocking your library...",
  "Waking up your study system...",
  "Gathering your 7 books...",
  "Brewing academic excellence...",
  "Assembling your comeback kit...",
  "Sharpening pencils...",
  "Dusting off the textbooks...",
  "Prepping your first-class materials...",
  "Loading brain fuel...",
  "Stacking the study stairs...",
  "Syncing with the grind...",
  "Packing your mentorship pass...",
  "Queueing up your 26-week journey...",
  "Charging your motivation...",
  "Fetching 'Get Good at Hard Things'...",
  "Building your study fortress...",
  "Warming up the welcome committee...",
  "Tuning your focus frequency...",
  "Locking in your discipline...",
  "Preparing your academic glow-up...",
  "Almost there — greatness takes a second...",
];
let statusRotationTimer = null;

function startStatusRotation() {
  const el = document.getElementById('poll-status-text');
  if (!el) return;
  let i = 0;
  el.textContent = POLL_STATUS_MESSAGES[0];
  stopStatusRotation();
  statusRotationTimer = setInterval(() => {
    i = (i + 1) % POLL_STATUS_MESSAGES.length;
    el.textContent = POLL_STATUS_MESSAGES[i];
  }, 2500);
}

function stopStatusRotation() {
  if (statusRotationTimer) { clearInterval(statusRotationTimer); statusRotationTimer = null; }
}

function startPolling() {
  document.getElementById('btn-check-payment').style.display = 'none';
  document.getElementById('poll-checking').style.display     = 'flex';
  startStatusRotation();
  pollStartedAt = Date.now();
  pollPayment();
}

async function pollPayment() {
  const elapsed = Date.now() - pollStartedAt;
  if (elapsed > POLL_MAX_ELAPSED_MS) {
    stopStatusRotation();
    document.getElementById('poll-checking').style.display     = 'none';
    document.getElementById('btn-check-payment').style.display = 'block';
    document.getElementById('btn-check-payment').textContent   = 'Check again ↺';
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/payments/verify`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        charge_id:      currentChargeId,
        va_id:          currentVaId,
        reference:      currentReference,
        email:          userEmail,
        name:           userName,
        payment_method: currentPayMethod,
      }),
    });
    const data = await res.json();

    if (data.success) {
      stopStatusRotation();
      clearPendingPayment();
      document.getElementById('payment-spinner').style.display = 'none';
      hideBankDetails();
      document.getElementById('payment-success').style.display = 'block';
      sessionStorage.setItem('ac_token', data.token);
      // Persist access — survives tab close, unlike sessionStorage
      if (data.magic_link) localStorage.setItem('ac_magic_link', data.magic_link);
      localStorage.setItem('ac_purchased', 'true');
      setTimeout(() => { window.location.href = '/welcome'; }, 1500);
      return;
    }

    // Not confirmed yet — retry with backoff
    pollingTimer = setTimeout(pollPayment, pollDelayFor(elapsed));
  } catch (err) {
    pollingTimer = setTimeout(pollPayment, pollDelayFor(elapsed));
  }
}

// ── Resume a pending payment on page load ────────────────────────────────────
// Covers the customer who transferred the money, then closed the tab or
// navigated away before tapping "I have made the transfer". Restores their
// reference/email and offers to re-check status without re-filling the form.
function showResumePaymentBanner(pending) {
  if (document.getElementById('resume-payment-banner')) return;

  const banner = document.createElement('div');
  banner.id = 'resume-payment-banner';
  banner.style.cssText = [
    'position:fixed', 'top:0', 'left:0', 'right:0', 'z-index:2000',
    'background:var(--ink)', 'color:#fff', 'padding:12px 16px',
    'display:flex', 'align-items:center', 'justify-content:center',
    'gap:12px', 'flex-wrap:wrap', 'text-align:center',
    'box-shadow:0 4px 12px rgba(0,0,0,0.3)', 'font-size:0.9rem',
  ].join(';');
  banner.innerHTML = `
    <span>You have a payment in progress for <strong>${pending.name || 'your order'}</strong>.</span>
    <button class="btn btn-primary" id="resume-payment-btn" style="padding:6px 14px;">Check my payment status</button>
    <button id="dismiss-resume-btn" style="background:none;border:none;color:var(--gold-l);cursor:pointer;text-decoration:underline;">Dismiss</button>
  `;
  document.body.prepend(banner);

  document.getElementById('resume-payment-btn').addEventListener('click', () => {
    userEmail        = pending.email;
    userName         = pending.name;
    currentChargeId  = pending.charge_id;
    currentReference = pending.reference;
    currentVaId      = pending.va_id;
    currentPayMethod = pending.payment_method;

    banner.remove();
    resetCheckout();
    openCheckout();
    showStep(2);
    document.getElementById('payment-spinner').style.display = 'none';
    if (pending.bank_details) showBankDetails(pending.bank_details);
    startPolling();
  });

  document.getElementById('dismiss-resume-btn').addEventListener('click', () => {
    banner.remove();
  });
}

(function resumePendingPaymentOnLoad() {
  const pending = loadPendingPayment();
  if (!pending || !pending.reference) return;

  // Silently check once in the background — if the webhook already
  // completed it, log the customer straight in with no banner at all.
  fetch(`${API_BASE}/payments/verify`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({
      charge_id:      pending.charge_id,
      va_id:          pending.va_id,
      reference:      pending.reference,
      email:          pending.email,
      name:           pending.name,
      payment_method: pending.payment_method,
    }),
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        clearPendingPayment();
        sessionStorage.setItem('ac_token', data.token);
        window.location.href = '/welcome';
        return;
      }
      showResumePaymentBanner(pending);
    })
    .catch(() => showResumePaymentBanner(pending));
})();

// ── Copy Account Number Helper ──────────────────────────────────────────────
function copyAccountNumber(text, buttonEl) {
  const cleanText = text.replace(/\D/g, '');
  const icon = buttonEl.querySelector('i');
  
  function showSuccess() {
    if (icon) {
      icon.className = 'bi bi-check-lg';
      icon.style.color = '#22c55e';
    }
    let tooltip = buttonEl.querySelector('.copy-tooltip');
    if (!tooltip) {
      tooltip = document.createElement('span');
      tooltip.className = 'copy-tooltip';
      tooltip.textContent = 'Copied!';
      tooltip.style.position = 'absolute';
      tooltip.style.right = '32px';
      tooltip.style.background = 'var(--ink)';
      tooltip.style.color = '#fff';
      tooltip.style.padding = '4px 8px';
      tooltip.style.borderRadius = '4px';
      tooltip.style.fontSize = '0.75rem';
      tooltip.style.border = '1px solid rgba(255,255,255,0.1)';
      tooltip.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
      tooltip.style.pointerEvents = 'none';
      tooltip.style.opacity = '0';
      tooltip.style.transition = 'opacity 0.2s';
      tooltip.style.whiteSpace = 'nowrap';
      tooltip.style.zIndex = '100';
      buttonEl.appendChild(tooltip);
    }
    setTimeout(() => { tooltip.style.opacity = '1'; }, 10);
    
    setTimeout(() => {
      if (icon) {
        icon.className = 'bi bi-copy';
        icon.style.color = '';
      }
      if (tooltip) {
        tooltip.style.opacity = '0';
        setTimeout(() => tooltip.remove(), 200);
      }
    }, 2000);
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(cleanText)
      .then(showSuccess)
      .catch(err => {
        console.error('Failed to copy using navigator.clipboard: ', err);
        fallbackCopy(cleanText);
      });
  } else {
    fallbackCopy(cleanText);
  }

  function fallbackCopy(val) {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = val;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      const successful = document.execCommand('copy');
      document.body.removeChild(textarea);
      if (successful) {
        showSuccess();
      } else {
        alert('Could not copy. Please select and copy manually.');
      }
    } catch (err) {
      console.error('Fallback copy failed: ', err);
      alert('Could not copy. Please select and copy manually.');
    }
  }
}
