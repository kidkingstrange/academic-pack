# Performance Audit & Mobile Constraints

## 1. Web Core Web Vitals Audit

| Metric | Current Static Baseline | Target Modern Next.js | Bottleneck / Mitigation |
| :--- | :--- | :--- | :--- |
| **LCP (Largest Contentful Paint)** | 1.8s - 2.4s | < 1.2s | High-resolution hero book covers in WebP format; implement `next/image` with automatic `priority` preloading. |
| **INP (Interaction to Next Paint)** | < 100ms | < 50ms | Vanilla JS DOM operations are lightweight; React state updates must avoid unnecessary re-renders. |
| **CLS (Cumulative Layout Shift)** | 0.02 | 0.00 | Ensure explicit `width` and `height` dimensions on all responsive image containers. |
| **TTFB (Time to First Byte)** | ~250ms - 450ms | < 150ms | Cloudflare Edge caching + Next.js ISR (Incremental Static Regeneration) on Vercel or CDN edge. |

---

## 2. Assets & Media Optimization
- **Image Compression:** The repository has already converted 379 images to modern `.webp` format in `frontend/assets/images/blog/`.
- **CSS Bundle Size:** Current `blog.css` is ~24KB uncompressed. Migrating to Tailwind CSS will purge unused styles, reducing critical CSS to < 10KB.
- **Font Optimization:** Currently links to Google Fonts via `<link>`. Next.js `next/font` will automatically self-host and inline critical font glyphs with zero layout shift.

---

## 3. Mobile Performance & Network Constraints (Flutter)
- **High Latency & Offline Tolerance:** In the primary market (Nigeria), 3G/4G connectivity can experience intermittent packet drops.
- **Offline Reading Architecture:** Flutter app must implement local encrypted storage using `hive` or `sqflite` + `flutter_secure_storage` to cache purchased PDF manuals for 100% offline reading.
- **Battery & Memory Hygiene:** In-app PDF rendering via `syncfusion_flutter_pdfviewer` or `pdfx` must release cached texture memory when navigating away from the reader.
