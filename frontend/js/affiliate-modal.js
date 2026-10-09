/**
 * Universal Affiliate Registration Modal & Floating Trigger
 * Built to match the Academic Comeback Swiss minimalist editorial design system.
 */
(function() {
  'use strict';

  var API_BASE = '/api';

  // ── CSS Styles ────────────────────────────────────────────────────────────
  function injectStyles() {
    var existing = document.getElementById('affiliate-modal-styles');
    if (existing) existing.remove();

    var style = document.createElement('style');
    style.id = 'affiliate-modal-styles';
    style.textContent = `
      /* ── Floating Affiliate Trigger Pill (Swiss Minimalist Editorial) ── */
      .aff-floating-trigger {
        position: fixed;
        bottom: 24px;
        left: 20px;
        z-index: 9998;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #0a0a0a;
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 9999px;
        padding: 7px 14px 7px 12px;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 12.5px;
        font-weight: 600;
        letter-spacing: -0.01em;
        line-height: 1;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        text-decoration: none;
        user-select: none;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.16), 0 1px 3px rgba(0, 0, 0, 0.08);
      }
      .aff-floating-trigger:hover {
        background: #1c1c1c;
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.24);
        border-color: rgba(255, 255, 255, 0.32);
      }
      .aff-floating-trigger__icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: #f59e0b;
        font-size: 13px;
        line-height: 1;
      }
      .aff-floating-trigger__label {
        color: #ffffff;
      }
      .aff-floating-trigger__sep {
        color: rgba(255, 255, 255, 0.35);
        font-weight: 400;
      }
      .aff-floating-trigger__reward {
        color: #f59e0b;
        font-weight: 700;
      }
      .aff-floating-trigger__arrow {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
        transition: transform 0.18s ease;
      }
      .aff-floating-trigger:hover .aff-floating-trigger__arrow {
        transform: translate(2px, -2px);
        color: #ffffff;
      }
      .aff-floating-trigger__dismiss {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        margin-left: 2px;
        border-radius: 50%;
        background: transparent;
        color: rgba(255, 255, 255, 0.4);
        font-size: 14px;
        line-height: 1;
        border: none;
        cursor: pointer;
        padding: 0;
        transition: color 0.15s, background 0.15s;
      }
      .aff-floating-trigger__dismiss:hover {
        color: #ffffff;
        background: rgba(255, 255, 255, 0.15);
      }

      /* Mobile adjustment to avoid sticky checkout bars */
      @media (max-width: 640px) {
        .aff-floating-trigger {
          bottom: 74px;
          left: 14px;
          padding: 6px 12px 6px 10px;
          font-size: 12px;
        }
      }

      /* ── Modal Overlay & Backdrop ── */
      .aff-modal-overlay {
        position: fixed;
        inset: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(10, 10, 10, 0.6);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100000;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.22s ease;
        padding: 16px;
        box-sizing: border-box;
      }
      .aff-modal-overlay.is-open {
        opacity: 1;
        pointer-events: auto;
      }

      /* ── Modal Card (Swiss Clean Editorial) ── */
      .aff-modal-card {
        background: #ffffff;
        color: #0a0a0a;
        border: 1px solid #e5e5e5;
        border-radius: 16px;
        max-width: 480px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        padding: 32px 28px;
        box-shadow: 0 20px 48px rgba(0, 0, 0, 0.2);
        position: relative;
        transform: translateY(14px) scale(0.98);
        transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        box-sizing: border-box;
      }
      .aff-modal-overlay.is-open .aff-modal-card {
        transform: translateY(0) scale(1);
      }

      /* Dark Theme Support for Blog */
      [data-theme="dark"] .aff-modal-card {
        background: #11141d;
        color: #f8fafc;
        border-color: rgba(255, 255, 255, 0.12);
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.6);
      }

      /* Close Button */
      .aff-modal-close {
        position: absolute;
        top: 18px;
        right: 18px;
        width: 32px;
        height: 32px;
        background: #f4f4f5;
        border: 1px solid #e4e4e7;
        border-radius: 50%;
        color: #09090b;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 13px;
        transition: all 0.18s ease;
        padding: 0;
      }
      .aff-modal-close:hover {
        background: #e4e4e7;
        color: #000;
      }
      [data-theme="dark"] .aff-modal-close {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.12);
        color: #cbd5e1;
      }
      [data-theme="dark"] .aff-modal-close:hover {
        background: rgba(255, 255, 255, 0.16);
        color: #fff;
      }

      /* Header */
      .aff-modal-header {
        text-align: left;
        margin-bottom: 22px;
        padding-right: 28px;
      }
      .aff-modal-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #b45309;
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid rgba(245, 158, 11, 0.25);
        padding: 3px 10px;
        border-radius: 9999px;
        margin-bottom: 10px;
      }
      [data-theme="dark"] .aff-modal-badge {
        color: #fbbf24;
        background: rgba(245, 158, 11, 0.15);
      }
      .aff-modal-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        color: #0a0a0a;
        letter-spacing: -0.035em;
        margin: 0 0 6px 0;
        line-height: 1.25;
      }
      [data-theme="dark"] .aff-modal-title {
        color: #ffffff;
      }
      .aff-modal-sub {
        font-size: 0.88rem;
        color: #595959;
        line-height: 1.5;
        margin: 0;
      }
      [data-theme="dark"] .aff-modal-sub {
        color: #94a3b8;
      }

      /* Form Elements */
      .aff-form-group {
        margin-bottom: 14px;
        text-align: left;
        position: relative;
      }
      .aff-form-label {
        display: block;
        font-size: 0.78rem;
        font-weight: 600;
        color: #595959;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 6px;
      }
      [data-theme="dark"] .aff-form-label {
        color: #94a3b8;
      }
      .aff-form-input {
        width: 100%;
        box-sizing: border-box;
        background: #ffffff;
        border: 1px solid #e5e5e5;
        color: #0a0a0a;
        padding: 11px 14px;
        border-radius: 8px;
        font-size: 15px; /* avoids iOS zoom */
        font-family: inherit;
        outline: none;
        transition: border-color 0.18s, box-shadow 0.18s;
      }
      .aff-form-input:focus {
        border-color: #0a0a0a;
        box-shadow: 0 0 0 1px #0a0a0a;
      }
      [data-theme="dark"] .aff-form-input {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(255, 255, 255, 0.15);
        color: #ffffff;
      }
      [data-theme="dark"] .aff-form-input:focus {
        border-color: #ffffff;
        box-shadow: 0 0 0 1px #ffffff;
      }

      .aff-form-divider {
        margin: 18px 0 12px;
        font-size: 0.72rem;
        font-weight: 700;
        color: #71717a;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        border-bottom: 1px solid #e5e5e5;
        padding-bottom: 6px;
      }
      [data-theme="dark"] .aff-form-divider {
        color: #94a3b8;
        border-color: rgba(255, 255, 255, 0.1);
      }

      .aff-bank-suggestions {
        display: none;
        position: absolute;
        top: calc(100% + 4px);
        left: 0;
        right: 0;
        z-index: 30;
        background: #ffffff;
        border: 1px solid #e5e5e5;
        border-radius: 8px;
        max-height: 200px;
        overflow-y: auto;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
      }
      [data-theme="dark"] .aff-bank-suggestions {
        background: #181c28;
        border-color: rgba(255, 255, 255, 0.15);
        box-shadow: 0 16px 36px rgba(0, 0, 0, 0.5);
      }
      .aff-bank-option {
        padding: 9px 14px;
        cursor: pointer;
        color: #0a0a0a;
        font-size: 0.86rem;
        transition: background 0.12s;
      }
      .aff-bank-option:hover {
        background: #f4f4f5;
      }
      [data-theme="dark"] .aff-bank-option {
        color: #f1f5f9;
      }
      [data-theme="dark"] .aff-bank-option:hover {
        background: rgba(255, 255, 255, 0.08);
      }

      .aff-status-banner {
        display: none;
        font-size: 0.8rem;
        margin-top: 6px;
        padding: 7px 10px;
        border-radius: 6px;
        font-weight: 600;
      }

      .aff-submit-btn {
        width: 100%;
        background: #0a0a0a;
        color: #ffffff;
        border: 1px solid #0a0a0a;
        padding: 13px 20px;
        border-radius: 9999px;
        font-size: 0.92rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.18s ease;
        margin-top: 10px;
        font-family: inherit;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
      }
      .aff-submit-btn:hover {
        background: #262626;
        border-color: #262626;
      }
      .aff-submit-btn:disabled {
        opacity: 0.55;
        cursor: not-allowed;
      }
      [data-theme="dark"] .aff-submit-btn {
        background: #ffffff;
        color: #0a0a0a;
        border-color: #ffffff;
      }
      [data-theme="dark"] .aff-submit-btn:hover {
        background: #f1f5f9;
      }

      .aff-err-text {
        display: none;
        color: #dc2626;
        font-size: 0.82rem;
        margin-top: 8px;
        text-align: center;
        font-weight: 500;
      }

      /* ── Success Screen ── */
      .aff-success-state {
        display: none;
        text-align: center;
      }
      .aff-success-icon {
        width: 52px;
        height: 52px;
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        color: #059669;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin: 0 auto 16px;
      }
      [data-theme="dark"] .aff-success-icon {
        background: rgba(34, 197, 94, 0.15);
        border-color: rgba(34, 197, 94, 0.3);
        color: #4ade80;
      }
      .aff-link-box {
        display: flex;
        align-items: center;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 9px 12px;
        margin: 6px 0 14px;
        gap: 8px;
      }
      [data-theme="dark"] .aff-link-box {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(255, 255, 255, 0.12);
      }
      .aff-link-box-val {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-family: 'JetBrains Mono', monospace, sans-serif;
        font-size: 0.82rem;
        color: #0a0a0a;
        text-align: left;
      }
      [data-theme="dark"] .aff-link-box-val {
        color: #f59e0b;
      }
      .aff-copy-btn {
        background: #0a0a0a;
        border: 1px solid #0a0a0a;
        color: #ffffff;
        padding: 5px 12px;
        border-radius: 9999px;
        cursor: pointer;
        font-size: 0.78rem;
        font-weight: 600;
        transition: all 0.18s ease;
        flex-shrink: 0;
      }
      .aff-copy-btn:hover {
        background: #262626;
      }
      [data-theme="dark"] .aff-copy-btn {
        background: rgba(245, 158, 11, 0.15);
        border-color: rgba(245, 158, 11, 0.3);
        color: #f59e0b;
      }
      [data-theme="dark"] .aff-copy-btn:hover {
        background: rgba(245, 158, 11, 0.28);
      }

      @media (max-width: 480px) {
        .aff-modal-card {
          padding: 24px 20px;
          border-radius: 14px;
        }
        .aff-modal-title {
          font-size: 1.25rem;
        }
      }
    `;
    document.head.appendChild(style);
  }

  // ── Modal Markup Injection ────────────────────────────────────────────────
  function injectModalMarkup() {
    var existingOverlay = document.getElementById('affiliate-modal-overlay');
    if (existingOverlay) existingOverlay.remove();

    var overlay = document.createElement('div');
    overlay.id = 'affiliate-modal-overlay';
    overlay.className = 'aff-modal-overlay';
    overlay.innerHTML = `
      <div class="aff-modal-card" id="aff-modal-card" role="dialog" aria-modal="true" aria-labelledby="aff-modal-title">
        <button type="button" class="aff-modal-close" id="aff-modal-close-btn" aria-label="Close modal"><i class="bi bi-x-lg"></i></button>
        
        <!-- Registration Form View -->
        <div id="aff-modal-form-view">
          <div class="aff-modal-header">
            <span class="aff-modal-badge"><i class="bi bi-award-fill"></i> AMBASSADOR PROGRAM</span>
            <h2 class="aff-modal-title" id="aff-modal-title">Become an Official Ambassador</h2>
            <p class="aff-modal-sub">Earn <strong style="color:#0a0a0a;">60% (₦3,000)</strong> on every ₦5,000 package sale. Direct automated bank payouts + <strong style="color:#15803d;">₦10,000 cash bonus</strong> on your first 10 sales.</p>
          </div>

          <form id="aff-modal-register-form" autocomplete="off">
            <div class="aff-form-group">
              <label class="aff-form-label" for="aff-m-name">Full Name</label>
              <input type="text" class="aff-form-input" id="aff-m-name" placeholder="e.g. Chidi Okafor" required>
            </div>

            <div class="aff-form-group">
              <label class="aff-form-label" for="aff-m-email">Email Address</label>
              <input type="email" class="aff-form-input" id="aff-m-email" placeholder="your@email.com" required>
            </div>

            <div class="aff-form-group">
              <label class="aff-form-label" for="aff-m-pwd">Password (min. 8 characters)</label>
              <input type="password" class="aff-form-input" id="aff-m-pwd" placeholder="Create a password" required minlength="8" autocomplete="new-password">
            </div>

            <div class="aff-form-divider">
              Payout Bank Details (Instant Direct Deposits)
            </div>

            <div class="aff-form-group">
              <label class="aff-form-label" for="aff-m-bank">Bank Name</label>
              <input type="text" class="aff-form-input" id="aff-m-bank" placeholder="Start typing bank name..." autocomplete="off" required>
              <input type="hidden" id="aff-m-bank-code">
              <div id="aff-m-bank-suggestions" class="aff-bank-suggestions"></div>
            </div>

            <div class="aff-form-group">
              <label class="aff-form-label" for="aff-m-acct">10-Digit Account Number</label>
              <input type="text" class="aff-form-input" id="aff-m-acct" placeholder="e.g. 0123456789" maxlength="10" pattern="[0-9]{10}" required>
              <div id="aff-m-acct-status" class="aff-status-banner"></div>
            </div>

            <div class="aff-form-group">
              <label class="aff-form-label" for="aff-m-acct-name">Account Name (Full name on bank account)</label>
              <input type="text" class="aff-form-input" id="aff-m-acct-name" placeholder="Full name on your bank account" required>
            </div>

            <button type="submit" class="aff-submit-btn" id="aff-m-submit-btn">
              Get My Ambassador Link <span style="font-size:1.05em">↗</span>
            </button>
            <p class="aff-err-text" id="aff-m-err"></p>

            <div style="margin-top:16px; text-align:center; font-size:0.82rem; color:#71717a;">
              Already registered? <a href="/affiliate/login" style="color:#0a0a0a; font-weight:600; text-decoration:underline;">Log In</a>
            </div>
          </form>
        </div>

        <!-- Success View -->
        <div id="aff-modal-success-view" class="aff-success-state">
          <div class="aff-success-icon"><i class="bi bi-check-lg"></i></div>
          <h2 class="aff-modal-title">You're an Official Ambassador!</h2>
          <p class="aff-modal-sub" style="margin-bottom:18px;">Your personal referral link is live right now. Share it with students to start earning ₦3,000 on every sale.</p>

          <div style="text-align:left; font-size:0.75rem; color:#71717a; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">
            Your Sales Link (Takes students to ₦5,000 package)
          </div>
          <div class="aff-link-box">
            <span class="aff-link-box-val" id="aff-m-sales-link"></span>
            <button type="button" class="aff-copy-btn" id="aff-m-copy-sales">Copy</button>
          </div>

          <div style="text-align:left; font-size:0.75rem; color:#15803d; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">
            Ambassador Recruiter Link (Invite others &amp; earn ₦5,000 bonus)
          </div>
          <div class="aff-link-box" style="border-color:#bbf7d0; background:#f0fdf4;">
            <span class="aff-link-box-val" id="aff-m-recruit-link" style="color:#15803d;"></span>
            <button type="button" class="aff-copy-btn" id="aff-m-copy-recruit">Copy</button>
          </div>

          <div style="margin:18px 0 10px;">
            <a id="aff-m-portal-btn" href="/affiliate/dashboard" class="aff-submit-btn" style="text-decoration:none;">
              Open My Ambassador Portal Now ↗
            </a>
          </div>

          <p style="font-size:0.78rem; color:#71717a; line-height:1.45; margin:10px 0 0;">
            Tip: Copy your links and save them in your WhatsApp starred notes.
          </p>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    // ── Floating Action Trigger Pill (Swiss Minimalist Editorial) ──
    var existingTrigger = document.getElementById('aff-floating-trigger');
    if (existingTrigger) existingTrigger.remove();

    try {
      if (!sessionStorage.getItem('aff_pill_dismissed')) {
        var trigger = document.createElement('div');
        trigger.id = 'aff-floating-trigger';
        trigger.className = 'aff-floating-trigger';
        trigger.setAttribute('role', 'button');
        trigger.setAttribute('tabindex', '0');
        trigger.setAttribute('aria-label', 'Open Ambassador Registration Modal');
        trigger.innerHTML = `
          <span class="aff-floating-trigger__icon"><i class="bi bi-gift-fill"></i></span>
          <span class="aff-floating-trigger__label">Become an Affiliate</span>
          <span class="aff-floating-trigger__sep">·</span>
          <span class="aff-floating-trigger__reward">Earn 60%</span>
          <span class="aff-floating-trigger__arrow">↗</span>
          <button type="button" class="aff-floating-trigger__dismiss" id="aff-trigger-dismiss" title="Dismiss" aria-label="Dismiss"><i class="bi bi-x"></i></button>
        `;
        document.body.appendChild(trigger);

        trigger.addEventListener('click', function(e) {
          if (e.target.closest('#aff-trigger-dismiss')) {
            e.stopPropagation();
            trigger.style.display = 'none';
            try { sessionStorage.setItem('aff_pill_dismissed', '1'); } catch (_) {}
            return;
          }
          openAffiliateRegisterModal();
        });
      }
    } catch (_) {}

    bindModalEvents();
  }

  // ── Open / Close Handlers ────────────────────────────────────────────────
  function openAffiliateRegisterModal() {
    var overlay = document.getElementById('affiliate-modal-overlay');
    if (!overlay) {
      injectModalMarkup();
      overlay = document.getElementById('affiliate-modal-overlay');
    }
    if (overlay) {
      overlay.classList.add('is-open');
      document.body.style.overflow = 'hidden';
      setTimeout(function() {
        var nameInput = document.getElementById('aff-m-name');
        if (nameInput) nameInput.focus();
      }, 100);
    }
  }

  function closeAffiliateRegisterModal() {
    var overlay = document.getElementById('affiliate-modal-overlay');
    if (overlay) {
      overlay.classList.remove('is-open');
      document.body.style.overflow = '';
    }
  }

  window.openAffiliateRegisterModal = openAffiliateRegisterModal;
  window.closeAffiliateRegisterModal = closeAffiliateRegisterModal;

  // ── Bank Data & Verification Logic ───────────────────────────────────────
  var allBanks = [
    { name: 'Access Bank', code: '044' },
    { name: 'Access Bank (Diamond)', code: '063' },
    { name: 'ALAT by Wema', code: '035A' },
    { name: 'Carbon', code: '565' },
    { name: 'Citibank Nigeria', code: '023' },
    { name: 'Ecobank Nigeria', code: '050' },
    { name: 'FairMoney MFB', code: '51318' },
    { name: 'Fidelity Bank', code: '070' },
    { name: 'First Bank of Nigeria', code: '011' },
    { name: 'First City Monument Bank (FCMB)', code: '214' },
    { name: 'Globus Bank', code: '00103' },
    { name: 'Guaranty Trust Bank (GTBank)', code: '058' },
    { name: 'Jaiz Bank', code: '301' },
    { name: 'Keystone Bank', code: '082' },
    { name: 'Kuda Bank', code: '50211' },
    { name: 'Lotus Bank', code: '303' },
    { name: 'Moniepoint Microfinance Bank', code: '50515' },
    { name: 'Nova Merchant Bank', code: '561' },
    { name: 'OPay', code: '999992' },
    { name: 'Palmpay', code: '999991' },
    { name: 'Parallex Bank', code: '526' },
    { name: 'Paycom (OPay)', code: '999992' },
    { name: 'Polaris Bank', code: '076' },
    { name: 'PremiumTrust Bank', code: '105' },
    { name: 'Providus Bank', code: '101' },
    { name: 'Rubies Bank', code: '125' },
    { name: 'SafeHaven MFB', code: '51113' },
    { name: 'Stanbic IBTC Bank', code: '221' },
    { name: 'Standard Chartered Bank', code: '068' },
    { name: 'Sterling Bank', code: '232' },
    { name: 'TAJBank', code: '302' },
    { name: 'Titan Trust Bank', code: '102' },
    { name: 'Union Bank of Nigeria', code: '032' },
    { name: 'United Bank for Africa (UBA)', code: '033' },
    { name: 'Unity Bank', code: '215' },
    { name: 'VFD Microfinance Bank (VBank)', code: '566' },
    { name: 'Wema Bank', code: '035' },
    { name: 'Zenith Bank', code: '057' },
    { name: 'Other Commercial / Microfinance Bank', code: '' }
  ];

  var BANK_ALIASES = {
    gtb: 'guarantytrust',
    gtbank: 'guarantytrust',
    uba: 'unitedbankforafrica',
    fcmb: 'firstcitymonument'
  };

  function normalize(s) {
    return s.toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  function bankMatches(bank, rawQuery) {
    var q = rawQuery.toLowerCase().trim();
    if (!q) return false;
    if (bank.name.toLowerCase().indexOf(q) !== -1) return true;
    var normQ = normalize(q);
    var normName = normalize(bank.name);
    if (normName.indexOf(normQ) !== -1) return true;
    var alias = BANK_ALIASES[normQ];
    return !!(alias && normName.indexOf(alias) !== -1);
  }

  function loadBanks() {
    fetch(API_BASE + '/affiliates/banks')
      .then(function(res) { return res.json(); })
      .then(function(json) {
        if (json && Array.isArray(json.banks) && json.banks.length > 0) {
          allBanks = json.banks.concat([{ name: 'Other Commercial / Microfinance Bank', code: '' }]);
        }
      })
      .catch(function() {});
  }

  function copyText(text, btn) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function() {
        var prev = btn.textContent;
        btn.textContent = 'Copied! ✓';
        setTimeout(function() { btn.textContent = prev; }, 2000);
      });
    } else {
      var ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      var prev = btn.textContent;
      btn.textContent = 'Copied! ✓';
      setTimeout(function() { btn.textContent = prev; }, 2000);
    }
  }

  // ── Bind Modal Events ────────────────────────────────────────────────────
  function bindModalEvents() {
    var overlay = document.getElementById('affiliate-modal-overlay');
    var closeBtn = document.getElementById('aff-modal-close-btn');
    var form = document.getElementById('aff-modal-register-form');
    var bankInput = document.getElementById('aff-m-bank');
    var bankCodeInput = document.getElementById('aff-m-bank-code');
    var bankSuggestions = document.getElementById('aff-m-bank-suggestions');
    var acctInput = document.getElementById('aff-m-acct');
    var acctNameInput = document.getElementById('aff-m-acct-name');
    var statusDiv = document.getElementById('aff-m-acct-status');
    var submitBtn = document.getElementById('aff-m-submit-btn');
    var errEl = document.getElementById('aff-m-err');

    if (!overlay || !form) return;

    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) closeAffiliateRegisterModal();
    });
    if (closeBtn) {
      closeBtn.addEventListener('click', closeAffiliateRegisterModal);
    }

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') closeAffiliateRegisterModal();
    });

    var filteredBanks = [];
    function renderSuggestions() {
      if (!filteredBanks.length) {
        bankSuggestions.style.display = 'none';
        bankSuggestions.innerHTML = '';
        return;
      }
      bankSuggestions.innerHTML = filteredBanks.map(function(b, i) {
        return '<div class="aff-bank-option" data-idx="' + i + '">' + b.name + '</div>';
      }).join('');
      bankSuggestions.style.display = 'block';
    }

    bankInput.addEventListener('input', function() {
      bankCodeInput.value = '';
      var q = bankInput.value.trim().toLowerCase();
      if (!q) {
        filteredBanks = [];
        renderSuggestions();
        return;
      }
      filteredBanks = allBanks.filter(function(b) { return bankMatches(b, q); }).slice(0, 30);
      renderSuggestions();
    });

    bankSuggestions.addEventListener('mousedown', function(e) {
      var opt = e.target.closest('.aff-bank-option');
      if (!opt) return;
      e.preventDefault();
      var idx = parseInt(opt.getAttribute('data-idx'), 10);
      var chosen = filteredBanks[idx];
      if (chosen) {
        bankInput.value = chosen.name;
        bankCodeInput.value = chosen.code || '';
        bankSuggestions.style.display = 'none';
        checkAccount();
      }
    });

    document.addEventListener('click', function(e) {
      if (!e.target.closest('#aff-m-bank') && !e.target.closest('#aff-m-bank-suggestions')) {
        bankSuggestions.style.display = 'none';
      }
    });

    function checkAccount() {
      var raw = acctInput.value.replace(/\D/g, '');
      acctInput.value = raw;
      statusDiv.style.display = 'none';

      if (raw.length !== 10) return;
      var code = bankCodeInput.value;
      if (!code) {
        statusDiv.style.display = 'block';
        statusDiv.style.background = '#fef2f2';
        statusDiv.style.color = '#dc2626';
        statusDiv.style.border = '1px solid #fecaca';
        statusDiv.innerHTML = 'Please select your bank above first';
        return;
      }

      statusDiv.style.display = 'block';
      statusDiv.style.background = '#fffbeb';
      statusDiv.style.color = '#b45309';
      statusDiv.style.border = '1px solid #fde68a';
      statusDiv.innerHTML = 'Verifying account with NIBSS...';

      fetch(API_BASE + '/affiliates/resolve-bank?account_number=' + raw + '&bank_code=' + code)
        .then(function(res) { return res.json(); })
        .then(function(data) {
          if (data && data.status && data.account_name) {
            statusDiv.style.background = '#f0fdf4';
            statusDiv.style.color = '#15803d';
            statusDiv.style.border = '1px solid #bbf7d0';
            statusDiv.innerHTML = 'Account Verified: <strong>' + data.account_name + '</strong>';
            acctNameInput.value = data.account_name;
          } else {
            statusDiv.style.background = '#fef2f2';
            statusDiv.style.color = '#dc2626';
            statusDiv.style.border = '1px solid #fecaca';
            statusDiv.innerHTML = ((data && data.detail) || 'Could not verify account name');
          }
        })
        .catch(function() {
          statusDiv.style.display = 'none';
        });
    }

    acctInput.addEventListener('input', checkAccount);

    form.addEventListener('submit', function(e) {
      e.preventDefault();
      errEl.style.display = 'none';

      var name = document.getElementById('aff-m-name').value.trim();
      var email = document.getElementById('aff-m-email').value.trim();
      var pwd = document.getElementById('aff-m-pwd').value;
      var bankName = bankInput.value.trim();
      var bankCode = bankCodeInput.value;
      var acct = acctInput.value.trim().replace(/\D/g, '');
      var acctName = acctNameInput.value.trim();

      if (pwd.length < 8) {
        errEl.textContent = 'Password must be at least 8 characters long.';
        errEl.style.display = 'block';
        return;
      }
      if (acct.length !== 10) {
        errEl.textContent = 'Account number must be exactly 10 digits.';
        errEl.style.display = 'block';
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Registering…';

      var payload = {
        name: name,
        email: email,
        password: pwd,
        bank_name: bankName,
        bank_code: bankCode,
        account_number: acct,
        account_name: acctName
      };

      fetch(API_BASE + '/affiliates/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(function(res) {
        return res.json().then(function(data) {
          if (!res.ok) {
            var msg = data.detail;
            if (Array.isArray(msg)) msg = msg.map(function(m) { return m.msg || m; }).join(' ');
            throw new Error(msg || 'Registration failed');
          }
          return data;
        });
      })
      .then(function(data) {
        if (data.access_token) {
          try { localStorage.setItem('affiliate_token', data.access_token); } catch(_) {}
        }
        if (data.dashboard_link) {
          try {
            var urlObj = new URL(data.dashboard_link, window.location.origin);
            var token = urlObj.searchParams.get('token');
            if (token) localStorage.setItem('affiliate_dashboard_token', token);
          } catch(_) {}
        }

        if (typeof fbq === 'function' && data.code) {
          fbq('track', 'CompleteRegistration', {}, { eventID: data.code });
        }

        document.getElementById('aff-modal-form-view').style.display = 'none';
        var succ = document.getElementById('aff-modal-success-view');
        succ.style.display = 'block';

        var sLink = document.getElementById('aff-m-sales-link');
        sLink.textContent = data.referral_link;
        sLink.title = data.referral_link;
        document.getElementById('aff-m-copy-sales').onclick = function() {
          copyText(data.referral_link, this);
        };

        var rLink = document.getElementById('aff-m-recruit-link');
        var recruitUrl = data.affiliate_invite_link || (window.location.origin + '/affiliate/register?invite=' + data.code);
        rLink.textContent = recruitUrl;
        rLink.title = recruitUrl;
        document.getElementById('aff-m-copy-recruit').onclick = function() {
          copyText(recruitUrl, this);
        };

        var portalBtn = document.getElementById('aff-m-portal-btn');
        if (portalBtn && data.dashboard_link) {
          portalBtn.href = data.dashboard_link;
        }
      })
      .catch(function(err) {
        errEl.textContent = err.message || 'Registration failed. Please try again.';
        errEl.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Get My Ambassador Link <span style="font-size:1.05em">↗</span>';
      });
    });
  }

  // ── Intercept All Affiliate Links Across the Current Page ────────────────
  function interceptAffiliateLinks() {
    document.addEventListener('click', function(e) {
      var link = e.target.closest('a[href*="affiliate-register"], a[href*="affiliate/register"], [data-open-affiliate-modal]');
      if (link) {
        e.preventDefault();
        openAffiliateRegisterModal();
      }
    });
  }

  // ── Initialization ───────────────────────────────────────────────────────
  function init() {
    injectStyles();
    injectModalMarkup();
    loadBanks();
    interceptAffiliateLinks();

    try {
      var params = new URLSearchParams(window.location.search);
      if (params.get('affiliate') === 'register' || params.get('join') === 'affiliate' || window.location.hash === '#affiliate-register') {
        setTimeout(openAffiliateRegisterModal, 300);
      }
    } catch (_) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
