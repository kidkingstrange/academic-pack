# Security & Compliance Audit

## 1. Authentication & Session Security
- **JWT (JSON Web Tokens):** Uses standard HS256 algorithm with `JWT_SECRET`. Tokens have expiration timestamps (`exp`) and role claims (`admin`, `affiliate`).
- **Password Hashing:** Passwords in `admin_accounts` and `affiliates` are hashed using `passlib`'s `bcrypt` with automated salt generation.
- **Student Library Access:** Digital library operates passwordless using cryptographically random `library_access_token` hashes. Signed PDF download URLs expire after 10 minutes (`JWT_DOWNLOAD_EXPIRE_MINUTES`).
- **Deficiency Identified:** The application lacks a centralized refresh token rotation mechanism for long-lived sessions on mobile devices. Flutter mobile integration requires secure refresh token handling in `flutter_secure_storage`.

---

## 2. Payment & Financial Security
- **Server-Side Price Validation:** The backend never trusts client-submitted prices or currencies. When a checkout session initializes, the backend recalculates prices from `backend/config.py` and canonical product data.
- **Webhook Signature Verification:**
  - **Paystack:** Verified using `x-paystack-signature` computed via HMAC SHA512 against the raw request body and `PAYSTACK_SECRET_KEY`.
  - **Flutterwave:** Verified using `verif-hash` matching `FLW_SECRET_HASH`.
- **Idempotency & Replay Attack Defense:** Every payment reference is enforced with a MongoDB unique index (`db.payments.create_index("reference", unique=True)`). Re-sent webhooks do not duplicate product fulfillment or affiliate commissions.
- **Affiliate Balance Check Guard:** Before executing any Flutterwave bank transfer, the payout service queries Flutterwave's live NGN balance API (`get_ngn_balance()`) to verify adequate funds.

---

## 3. Data Protection & Compliance (NDPA 2023 & CAN-SPAM)
- **Marketing Consent Enforcement:** Every outgoing marketing broadcast filters recipients against `recovery_unsubscribes` and checks `is_active: True`.
- **1-Click Unsubscribe:** All transactional and promotional emails include mandatory `List-Unsubscribe` email headers and visible footer links.
- **Physical Address Attribution:** All emails carry the registered physical publisher address ("Scale Group Digital Publishing, 8 The Scale Conference Blvd, Victoria Island, Lagos, Nigeria").

---

## 4. API Hardening & Network Security
- **Rate Limiting:** Implemented using `slowapi` with in-memory / Redis limits (e.g. 10/min on `/api/admin/login`, 5/min on payment initialization).
- **Security Headers:** The Nginx proxy configuration enforces:
  - `X-Frame-Options: SAMEORIGIN`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy`
