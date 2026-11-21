# Known Issues & Operational Remediation Log

## 1. Active Known Issues & Mitigations

| Issue Code | Description | Severity | Current Status | Remediation Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **ISSUE-001** | Outbound SMTP connection timeouts on Render (Port 465 & 587 to `mail.privateemail.com`) | High | Diagnosed | Cloud hosts (Render) restrict raw SMTP ports to prevent spam. Migrate outbound mail transport to transactional HTTP API (Resend, Brevo, or SendGrid API) instead of raw SMTP sockets. |
| **ISSUE-002** | Static HTML code duplication across 433 files | Medium | Active | Migrate frontend to Next.js component-driven architecture with App Router. |
| **ISSUE-003** | Lack of long-lived mobile session refresh tokens | Medium | Planned | Implement standard OAuth2/JWT refresh token rotation stored in `flutter_secure_storage`. |
| **ISSUE-004** | Untyped API calls in legacy frontend scripts | Low | Active | Generate shared TypeScript and Dart API contracts directly from FastAPI OpenAPI schema. |
| **ISSUE-005** | 18 catalog titles in `products.json` lack deliverable PDF assets | Low | Active | Enforce pre-order / waitlist status for these 18 titles until content authoring is complete. |
