# Deployment & Multi-Platform Hosting Guide

## 1. Multi-Platform Hosting Architecture

| Platform Surface | Hosting / Distribution Provider | Deployment Mechanism | URL / Target Identifier |
| :--- | :--- | :--- | :--- |
| **Website (Next.js)** | Vercel / Render Static | Git push on `main` $\rightarrow$ Edge CDN | `https://academiccomeback.com` |
| **Android Application** | Google Play Store | GitHub Actions $\rightarrow$ Fastlane / Play Console | `com.scalegroup.academiccomeback` |
| **iOS Application** | Apple App Store / TestFlight | Xcode Cloud / Fastlane | `com.scalegroup.academiccomeback` |
| **Backend API** | Render (Web Service) | Docker container on `origin/main` push | `https://edgepack.thescaleconference.com` |
| **Database** | MongoDB Atlas Cluster | M10+ Managed Replica Set (Automated Backups) | Dedicated Cloud VPC |

---

## 2. Environment Configuration & CI/CD Pipeline

### Next.js Website Environment (`apps/website/.env.production`)
```env
NEXT_PUBLIC_APP_URL=https://academiccomeback.com
NEXT_PUBLIC_API_URL=https://edgepack.thescaleconference.com
NEXT_PUBLIC_PAYSTACK_KEY=pk_live_xxxx
NEXT_PUBLIC_FLUTTERWAVE_KEY=FLWPUBK-xxxx
NEXT_PUBLIC_FB_PIXEL_ID=1033231049261122
```

### Flutter Mobile App Configuration (`apps/mobile/lib/core/constants/app_config.dart`)
```dart
class AppConfig {
  static const String apiBaseUrl = "https://edgepack.thescaleconference.com";
  static const String appName = "Academic Comeback";
  static const String paystackPublicKey = "pk_live_xxxx";
}
```

---

## 3. Safe Zero-Downtime Rollout Strategy
1. **Maintain Live Backend:** The backend continues serving live traffic without downtime.
2. **Parallel Staging Deployment:** Next.js and Flutter are deployed to staging environments (`stage.academiccomeback.com` & internal TestFlight/Play Internal Track).
3. **DNS Cutover with 301 Rules:** Once tested, DNS routes web traffic to Next.js while 301 redirects preserve every legacy static URL.
