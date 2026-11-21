# Database Architecture & Migration Audit

## 1. Current Database Engine: MongoDB Atlas
The existing database is an asynchronous **MongoDB** replica set accessed via the **Motor** Python driver (`AsyncIOMotorClient`). All database models are dynamically shaped documents validated via **Pydantic v2** at the API layer.

---

## 2. Collection Inventory & Index Map

| Collection Name | Purpose | Key Fields | Primary & Compound Indexes |
| :--- | :--- | :--- | :--- |
| `users` | Registered customers & library accounts | `email`, `name`, `purchased_products`, `library_access_token`, `is_active` | `email` (Unique), `library_access_token` (Unique, Sparse) |
| `payments` | Completed financial transactions | `reference`, `email`, `amount`, `currency`, `product_slug`, `product_name`, `gateway`, `status`, `items` | `reference` (Unique), `[("email", 1), ("status", 1)]`, `created_at` |
| `pending_payments` | Unverified checkout sessions | `reference`, `email`, `amount`, `product_slug`, `affiliate_code`, `status` | `reference` (Unique) |
| `subscribers` | 52-week curriculum drip list | `email`, `name`, `sequence_position`, `is_active`, `unsubscribe_token` | `email` (Unique), `unsubscribe_token` (Unique, Sparse) |
| `email_queue` | Outbound email delivery queue | `email`, `kind`, `campaign_id`, `status`, `scheduled_at`, `attempts`, `error` | `[("status", 1), ("scheduled_at", 1)]`, `[("kind", 1), ("status", 1)]`, `email` |
| `affiliates` | Referral partners & ambassadors | `code`, `email`, `name`, `commission_rate`, `bank_code`, `account_number`, `dashboard_token` | `code` (Unique), `email` (Unique), `dashboard_token` (Unique), `invited_by` |
| `referrals` | Commission transaction records | `reference`, `affiliate_code`, `order_amount`, `commission_amount`, `commission_status` | `reference` (Unique), `[("affiliate_code", 1), ("commission_status", 1)]`, `created_at` |
| `payout_batches` | Biweekly Flutterwave transfers | `batch_id`, `total_amount`, `affiliates_count`, `transfers`, `status` | `created_at` (-1), `status` |
| `products` | Product catalog metadata | `slug`, `title`, `price_naira`, `price_usd`, `category`, `description`, `is_active` | `slug` (Unique, Sparse), `[("is_active", 1), ("order", 1)]`, `title` |
| `reviews` | Customer ratings & feedback | `product_slug`, `rating`, `comment`, `customer_name`, `customer_token_hash`, `approved` | `customer_token_hash` (Unique, Sparse), `[("approved", 1), ("date", -1)]` |
| `abandoned_transactions` | Drop-off recovery records | `reference`, `email`, `phone`, `amount`, `recovery_step`, `status` | `reference` (Unique), `[("status", 1), ("created_at", -1)]`, `email` |
| `marketing_campaigns` | AI marketing broadcasts | `campaign_id`, `title`, `product_slug`, `target_segment`, `subject`, `html_body`, `status` | `campaign_id` (Unique), `[("status", 1), ("created_at", -1)]` |
| `marketing_logs` | Per-recipient marketing delivery logs | `campaign_id`, `email`, `status`, `sent_at`, `opened_at`, `clicked_at` | `[("campaign_id", 1), ("email", 1)]`, `[("status", 1), ("queued_at", -1)]` |
| `downloads` | Digital PDF access audit log | `user_id`, `product_id`, `ip_address`, `downloaded_at` | `[("user_id", 1), ("product_id", 1)]` |

---

## 3. Data Integrity & Concurrency Evaluation

1. **CAS (Compare-And-Swap) Concurrency:** The codebase uses atomic MongoDB `find_one_and_update()` operations with conditional filters to guarantee idempotency in:
   - Worker email queue claiming (`status: "pending" -> "processing"`).
   - Biweekly affiliate payout processing.
   - Subscription renewal billing.
2. **Denormalized Snapshots:** In `payments`, the system captures snapshots of `product_name`, `amount`, and `items` at the moment of purchase, protecting historical order ledgers against subsequent product renaming.
3. **Foreign Key Integrity Gap:** Because MongoDB is document-oriented, relationships between `referrals` and `affiliates`, or `downloads` and `users`, are loosely coupled. Dangling references can occur if records are deleted manually.

---

## 4. Target PostgreSQL + Prisma Relational Model

When migrating to PostgreSQL + Prisma, the 35 MongoDB collections translate into a normalized relational schema with explicit constraints:

```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model User {
  id                 String     @id @default(uuid())
  email              String     @unique
  name               String?
  libraryAccessToken String?    @unique
  isActive           Boolean    @default(true)
  createdAt          DateTime   @default(now())
  updatedAt          DateTime   @updatedAt

  orders             Order[]
  downloads          Download[]
  reviews            Review[]
}

model Product {
  id                 String     @id @default(uuid())
  slug               String     @unique
  title              String
  description        String
  priceNaira         Int
  priceUsd           Float
  category           String
  isActive           Boolean    @default(true)
  createdAt          DateTime   @default(now())

  orderItems         OrderItem[]
  reviews            Review[]
}

model Order {
  id                 String       @id @default(uuid())
  reference          String       @unique
  userId             String
  user               User         @relation(fields: [userId], references: [id])
  totalAmount        Float
  currency           String       @default("NGN")
  gateway            String       // "paystack" | "flutterwave"
  status             PaymentStatus @default(PENDING)
  affiliateCode      String?
  createdAt          DateTime     @default(now())

  items              OrderItem[]
  referral           Referral?
}

model OrderItem {
  id                 String     @id @default(uuid())
  orderId            String
  order              Order      @relation(fields: [orderId], references: [id])
  productId          String
  product            Product    @relation(fields: [productId], references: [id])
  productNameSnapshot String
  unitPrice          Float
  quantity           Int        @default(1)
}

enum PaymentStatus {
  PENDING
  SUCCESS
  FAILED
  REFUNDED
}
```

---

## 5. Migration & Dual-Run Strategy
- **Phase A (Zero Risk):** Retain live MongoDB as the operational source of truth while building the Next.js and Flutter frontends.
- **Phase B (Shadow Dual-Write):** Deploy an event-driven sync worker that replicates completed `payments`, `users`, and `orders` from MongoDB to PostgreSQL.
- **Phase C (Cutover):** Run checksum reconciliation between MongoDB and PostgreSQL. Switch read traffic to Prisma/PostgreSQL once data parity reaches 100%.
