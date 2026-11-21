# Backend REST API Audit & Contract Mapping

## 1. Overview
The platform currently exposes **81 REST endpoints** grouped into 10 domain routers. All endpoints are implemented in Python FastAPI with Pydantic v2 request/response models.

---

## 2. Router & Endpoint Inventory

### A. Payments & Checkout (`/api/payments`)
| Method | Route | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/payments/initialize` | Public | Initiates a Paystack/Flutterwave transaction, calculates price, records `pending_payments`. |
| `POST` | `/api/payments/verify` | Public | Verifies payment reference directly against gateway API, provisions user account. |
| `POST` | `/api/payments/webhook` | Webhook Secret | Idempotent callback processing for Paystack (SHA512) and Flutterwave (Secret Hash). |
| `GET` | `/api/payments/price` | Public | Returns current product pricing (checking promo dates dynamically). |
| `POST` | `/api/payments/abandoned/capture` | Public | Captures email/phone early on checkout modal blur to enable recovery drips. |

### B. Customer Library & Digital Access (`/api/library`)
| Method | Route | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/library/books` | Token | Validates `library_access_token` and lists user's purchased books. |
| `GET` | `/api/library/read/{slug}` | Token | Streams online book reader content for a specific purchased book. |
| `GET` | `/api/library/download/{slug}` | Token | Generates a 10-minute signed, expiring JWT URL to download a watermarked PDF. |

### C. Admin & Operations (`/api/admin`)
| Method | Route | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/admin/login` | Public (Rate-limited) | Authenticates administrator, returns JWT bearer token. |
| `GET` | `/api/admin/analytics` | Admin JWT | Aggregates sales KPIs, gross revenue, net payout breakdown, order count. |
| `GET` | `/api/admin/payments` | Admin JWT | Retrieves paginated order ledger with exact product items, buyer details, and timestamps. |
| `GET` | `/api/admin/users` | Admin JWT | Lists customer accounts, purchased products, and library activity. |
| `POST` | `/api/admin/products` | Admin JWT | Uploads new product PDF, extracts metadata, registers in catalog. |

### D. AI Marketing Engine (`/api/admin/marketing`)
| Method | Route | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/admin/marketing/overview` | Admin JWT | Real-time audience KPIs, consent breakdown, campaign performance. |
| `GET` | `/api/admin/marketing/products` | Admin JWT | Structured internal Product Knowledge Base (13 canonical offerings). |
| `GET` | `/api/admin/marketing/segments` | Admin JWT | Live recipient counts across 8 audience segments with automatic suppression. |
| `POST` | `/api/admin/marketing/generate-copy` | Admin JWT | AI copywriter synthesizing subject lines, preview text, and responsive HTML. |
| `POST` | `/api/admin/marketing/campaigns` | Admin JWT | Creates and saves a marketing broadcast draft or schedule. |
| `POST` | `/api/admin/marketing/campaigns/{id}/launch` | Admin JWT | Launches broadcast to consented recipients via rate-limited queue. |
| `POST` | `/api/admin/marketing/dispatch-preview-test` | Locked (`daviditoyaa@gmail.com`) | Dispatches immediate sample campaign email to verified admin inbox. |

### E. Affiliate Network (`/api/affiliates`)
| Method | Route | Auth | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/affiliates/register` | Public | Enrolls new affiliate, generates referral link and dashboard token. |
| `GET` | `/api/affiliates/dashboard` | Affiliate Token | Returns affiliate clicks, referrals, earned commissions, and rank. |
| `GET` | `/api/admin/payouts/batches` | Admin JWT | Lists biweekly Flutterwave payout batches with balance checks. |
| `POST` | `/api/admin/payouts/batches/{id}/approve` | Admin JWT | Executes bulk bank transfers to affiliate accounts. |

---

## 3. OpenAPI & Client Generation Strategy
1. **FastAPI OpenAPI Schema:** The current backend automatically exposes a standardized OpenAPI v3 JSON spec at `/openapi.json`.
2. **TypeScript Client Generation:** Using `@hey-api/openapi-ts` or `openapi-typescript-codegen`, we can automatically generate 100% type-safe TypeScript interfaces and API clients for the Next.js frontend.
3. **Dart Client Generation:** Using `swagger_dart_codegen` or custom Dio service repositories, the Flutter application inherits strongly typed model classes directly from the backend schema.
