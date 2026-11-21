# SEO Audit & Traffic Preservation Plan

## 1. Current Search Footprint & Equity
The platform possesses significant organic search authority, built upon **418 long-tail academic articles** located in `/frontend/blog/academics/`, plus multiple dedicated product landing pages.

### SEO Asset Inventory
- **Total Static HTML URLs:** 433 pages.
- **Top Organic Keywords:** Nigerian university study tips, 100-level transition guide, exam cramming panic plan, active recall study method, first-class student habits.
- **XML Sitemap:** Dynamic sitemap served at `/sitemap.xml`.
- **Robots.txt:** Configured to permit indexing of landing pages and blog articles while disallowing `/admin/`, `/library`, and `/api/`.

---

## 2. On-Page SEO Implementation Analysis

| SEO Component | Current Status | Issues / Deficiencies | Next.js Target Implementation |
| :--- | :--- | :--- | :--- |
| **Title Tags** | Present on all pages | Hardcoded in static HTML; lacks dynamic brand suffix consistency | Dynamic `generateMetadata()` in Next.js App Router |
| **Meta Descriptions** | Present on ~90% of posts | Some descriptions exceed 160 characters or repeat verbatim | Enforce character limits & distinct snippets via metadata schema |
| **Canonical Tags** | Present | Some point to `academiccomeback.com`, others to `thescaleconference.com` | Centralized `metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL)` |
| **Structured Data** | Basic Schema.org (`Article`, `BreadcrumbList`) | Hardcoded `<script type="application/ld+json">`, lacks Product offer schemas | Next.js Dynamic JSON-LD with `Product`, `Offer`, `BreadcrumbList`, `Article` |
| **Open Graph & Twitter** | Basic tags present | Inconsistent image aspect ratios across articles | Automated OG Image Generation via Next.js `@vercel/og` |
| **Heading Hierarchy** | Mostly semantic (`H1`, `H2`, `H3`) | Some landing pages have multiple `H1` tags | Strict component hierarchy (single `H1` per route) |

---

## 3. SEO Equity Preservation & 301 Redirect Architecture

During the migration to Next.js, **zero search rankings or backlinks must be lost**.

### URL Mapping Rules:
1. **Blog Articles:**
   - Current: `/blog/academics/[slug].html` and `/blog/academics/[slug]/index.html`
   - Target Next.js Route: `/blog/[category]/[slug]`
   - Permanent 301 Redirect: Any inbound traffic to `/blog/academics/:slug.html` automatically maps with HTTP 301 to `/blog/academics/:slug`.
2. **Product Landing Pages:**
   - Current: `/[product-slug].html` (e.g. `/quitting-the-handjob.html`)
   - Target Next.js Route: `/products/[slug]` (with transparent rewrite from `/[slug]`)
   - Permanent 301 Redirect: `/:slug.html` $\rightarrow$ `/:slug`

```javascript
// next.config.js - 301 Permanent Redirects
module.exports = {
  async redirects() {
    return [
      {
        source: '/blog/academics/:slug.html',
        destination: '/blog/academics/:slug',
        permanent: true,
      },
      {
        source: '/:slug.html',
        destination: '/:slug',
        permanent: true,
      },
    ];
  },
};
```
