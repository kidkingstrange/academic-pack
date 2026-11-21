# Target Modern E-Commerce Architecture

## 1. System Vision
The modernized platform transitions from a monolithic static HTML/CSS structure into a **unified three-surface e-commerce ecosystem** powered by a single, shared source of truth.

```mermaid
flowchart TD
    subgraph Frontends ["Three Independent Frontend Surfaces"]
        NextWeb["1. Next.js 15 Web Application\n(TypeScript, App Router, SSR/ISR, Tailwind)"]
        FlutterAndroid["2. Flutter Android Native App\n(Dart, Riverpod, Offline PDFs, Material 3)"]
        FlutterIOS["3. Flutter iOS Native App\n(Same Dart Codebase, Cupertino/Human Interface)"]
    end

    subgraph APIContract ["Shared API & Type Contract Layer"]
        OpenAPISpec["OpenAPI 3.1 Spec (/openapi.json)"]
        TSClient["Generated TypeScript SDK (@repo/api-client)"]
        DartClient["Generated Dart Repositories (api_service.dart)"]
    end

    subgraph CoreBackend ["Shared Central Backend"]
        FastAPI_Core["FastAPI High-Performance Engine\n(81+ Documented REST Endpoints)"]
        AuthModule["Unified Authentication & JWT Session Engine"]
        PaymentEngine["Universal Payment Gateway (Paystack & Flutterwave)"]
        OrderLedger["Immutable Order & Payout Reconciliation Ledger"]
        LibraryEngine["Student Digital Library & Watermarked PDF Streamer"]
        WorkerService["Background Event Workers (Drip, Recovery, Marketing)"]
    end

    subgraph DataStore ["Shared Persistent Storage"]
        MongoDB_Live[("MongoDB Atlas Primary Database\n(35+ Collections, Compound Indexes)")]
        Postgres_Target[("PostgreSQL + Prisma\n(Relational Target for Financial Ledger)")]
        SecureAssets["Encrypted PDF & Asset Storage"]
    end

    NextWeb --> TSClient --> FastAPI_Core
    FlutterAndroid --> DartClient --> FastAPI_Core
    FlutterIOS --> DartClient --> FastAPI_Core

    OpenAPISpec --> TSClient
    OpenAPISpec --> DartClient
    FastAPI_Core --> OpenAPISpec

    FastAPI_Core --> AuthModule
    FastAPI_Core --> PaymentEngine
    FastAPI_Core --> OrderLedger
    FastAPI_Core --> LibraryEngine
    FastAPI_Core --> WorkerService

    FastAPI_Core --> MongoDB_Live
    OrderLedger -.-> Postgres_Target
    LibraryEngine --> SecureAssets
```

---

## 2. Platform Uniformity Guarantees

1. **Shared Customer Accounts:** A student registering or purchasing on the Next.js website logs in immediately on Android and iOS using the same credentials or access tokens.
2. **Shared Product Catalogue & Prices:** A product added or updated via the Admin Dashboard synchronizes in real time across the website, Android app, and iOS app.
3. **Shared Purchase & Order History:** An order placed on an Android phone appears immediately on the customer's website dashboard and in the admin sales ledger.
4. **Universal Payment Verification:** Both mobile and web checkouts route through the same backend verification endpoints, ensuring zero price manipulation and idempotent fulfillment.

---

## 3. Project Directory Structure

```text
academic-pack/
├── apps/
│   ├── website/                 # Modern Next.js 15 + TypeScript Web App
│   │   ├── app/                 # App Router (SSR, SSG, ISR)
│   │   ├── components/          # Reusable UI & Checkout Components
│   │   ├── lib/                 # Next.js API client & utilities
│   │   └── public/              # Static assets & optimized WebP images
│   │
│   └── mobile/                  # Cross-Platform Flutter Mobile Application
│       ├── android/             # Android native configuration & Gradle
│       ├── ios/                 # iOS native Xcode project configuration
│       └── lib/
│           ├── core/            # Theme, design tokens, network (Dio), storage
│           ├── features/        # Auth, Catalog, Cart, Checkout, Reader, Affiliates
│           └── main.dart        # Application entrypoint
│
├── backend/                     # Central Python FastAPI High-Performance Backend
│   ├── routes/                  # REST API Endpoints (Admin, Payments, Library, Marketing)
│   ├── services/                # Business logic & payment services
│   ├── workers/                 # Background schedulers (Email, Cart recovery, Payouts)
│   └── database.py              # MongoDB Atlas connection & indexing
│
├── packages/
│   ├── shared-api-contracts/    # OpenAPI v3.1 schema & TypeScript/Dart generators
│   └── shared-documentation/    # Central system documentation & API references
│
└── docs/                        # Architecture, database, SEO & deployment guides
```
