/**
 * Scale Group / Academic Comeback - Shared API Contracts & Client
 * Strongly-typed definitions shared between Next.js Web and Backend.
 */

export interface Product {
  id: string;
  slug: string;
  title: string;
  description: string;
  priceNaira: number;
  regularPriceNaira: number;
  priceUsd: number;
  regularPriceUsd: number;
  category: string;
  benefits: string[];
  features: string[];
  targetAudience: string;
  coverImage: string;
  isDeliverable: boolean;
  isBundle?: boolean;
  tagline?: string;
  painPoints?: string[];
  chapters?: Array<{ number: string; title: string; summary: string }>;
  faqs?: Array<{ question: string; answer: string }>;
}

export interface PricingResponse {
  product_slug: string;
  price_naira: number;
  price_usd: number;
  regular_price_naira: number;
  regular_price_usd: number;
  is_promo_active: boolean;
  promo_end_date: string;
}

export interface PaymentInitRequest {
  email: string;
  name: string;
  product_slug: string;
  affiliate_code?: string;
  currency?: 'NGN' | 'USD';
  quantity?: number;
}

export interface PaymentInitResponse {
  reference: string;
  amount: number;
  currency: string;
  gateway: 'paystack' | 'flutterwave';
  authorization_url?: string;
  access_code?: string;
  public_key?: string;
}

export interface PaymentVerifyResponse {
  success: boolean;
  status: 'success' | 'failed' | 'pending';
  reference: string;
  amount: number;
  product_slug: string;
  product_name: string;
  library_access_token?: string;
  dashboard_link?: string;
  customer_email: string;
  customer_name: string;
}

export interface LibraryBook {
  slug: string;
  title: string;
  category: string;
  cover_image: string;
  download_url: string;
  read_url: string;
  purchased_at?: string;
}

export interface LibraryResponse {
  authenticated: boolean;
  email: string;
  library_access_token: string;
  books: LibraryBook[];
}

export interface AffiliateProfile {
  code: string;
  name: string;
  email: string;
  commission_rate: number;
  referral_url: string;
  total_clicks: number;
  total_referrals: number;
  total_earnings_naira: number;
  unpaid_earnings_naira: number;
}

export interface CustomerReview {
  id: string;
  product_slug: string;
  customer_name: string;
  rating: number;
  comment: string;
  verified_purchase: boolean;
  created_at: string;
}

export interface BlogPostMetadata {
  slug: string;
  title: string;
  description: string;
  category: string;
  author: string;
  published_at: string;
  featured_image: string;
  reading_time_minutes: number;
  canonical_url: string;
}

/**
 * Universal Typed API Client for Next.js & Web
 */
export class AcademicApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = process.env.NEXT_PUBLIC_API_URL || 'https://edgepack.thescaleconference.com') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
    const headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    };

    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        errorMsg = errorJson.detail || errorJson.message || errorMsg;
      } catch {
        // fallback to statusText
      }
      throw new Error(errorMsg);
    }

    return res.json() as Promise<T>;
  }

  // Pricing
  async getProductPricing(slug: string): Promise<PricingResponse> {
    return this.request<PricingResponse>(`/api/payments/price?product_slug=${encodeURIComponent(slug)}`);
  }

  // Checkout & Payments
  async initializePayment(payload: PaymentInitRequest): Promise<PaymentInitResponse> {
    return this.request<PaymentInitResponse>('/api/payments/initialize', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async verifyPayment(reference: string): Promise<PaymentVerifyResponse> {
    return this.request<PaymentVerifyResponse>('/api/payments/verify', {
      method: 'POST',
      body: JSON.stringify({ reference }),
    });
  }

  // Student Library
  async getLibrary(token: string): Promise<LibraryResponse> {
    return this.request<LibraryResponse>(`/api/library/books?token=${encodeURIComponent(token)}`);
  }

  async getSignedDownloadUrl(token: string, productSlug: string): Promise<{ download_url: string }> {
    return this.request<{ download_url: string }>(
      `/api/library/download/${encodeURIComponent(productSlug)}?token=${encodeURIComponent(token)}`
    );
  }

  // Reviews
  async getProductReviews(productSlug: string): Promise<CustomerReview[]> {
    return this.request<CustomerReview[]>(`/api/reviews/${encodeURIComponent(productSlug)}`);
  }
}
