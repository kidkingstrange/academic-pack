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
    const res = await fetch(`${API_BASE}/payments/initialize`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        name:           userName,
        email:          userEmail,
        client_expiry:  clientExpiry ? Number(clientExpiry) : null,
        payment_method: currentPayMethod,
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
      showBankDetails({
        account_number: data.account_number,
        bank_name:      data.bank_name,
        amount:         data.amount_with_fee || data.amount,
        base_amount:    data.amount,
        expiry:         data.expiry,
        note:           data.note,
      });
      return;
    }

    // Legacy bank_transfer from charge flow
    showBankDetails(data);

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
        <strong class="bank-detail-value acct-number">${data.account_number || '—'}</strong>
      </div>
      <div class="bank-detail-row">
        <span class="bank-detail-label">Amount</span>
        <strong class="bank-detail-value gold">${fmt}</strong>
      </div>
      ${expiryNote}
      <p class="bank-details-note">${data.note || 'Account is valid for 60 minutes. Transfer the exact amount.'}</p>
      <div id="poll-checking" style="display:none" class="poll-checking">
        <div class="mini-spinner"></div>
        <span>Checking for your payment...</span>
      </div>
      <button class="btn btn-primary btn-check-payment" id="btn-check-payment" onclick="startPolling()">
        I have made the transfer ✓
      </button>
    </div>`;
  bd.style.display = 'block';
}

// ── Polling — check every 10 seconds for up to ~3 minutes ────────────────────
function startPolling() {
  document.getElementById('btn-check-payment').style.display = 'none';
  document.getElementById('poll-checking').style.display     = 'flex';
  pollPayment(0);
}

async function pollPayment(attempt) {
  if (attempt > 18) { // ~3 minutes
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
      document.getElementById('payment-spinner').style.display = 'none';
      hideBankDetails();
      document.getElementById('payment-success').style.display = 'block';
      sessionStorage.setItem('ac_token', data.token);
      setTimeout(() => { window.location.href = '/welcome'; }, 1500);
      return;
    }

    // Not confirmed yet — retry
    pollingTimer = setTimeout(() => pollPayment(attempt + 1), 10000);
  } catch (err) {
    pollingTimer = setTimeout(() => pollPayment(attempt + 1), 10000);
  }
}
