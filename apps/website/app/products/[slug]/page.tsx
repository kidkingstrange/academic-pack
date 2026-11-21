import React from 'react';
import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { CANONICAL_PRODUCTS, getProductBySlug } from '@/lib/products';
import ProductClientView from './ProductClientView';

interface ProductPageProps {
  params: { slug: string };
}

export async function generateStaticParams() {
  return CANONICAL_PRODUCTS.map((p) => ({
    slug: p.slug,
  }));
}

export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  const product = getProductBySlug(params.slug);
  if (!product) return {};

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://academiccomeback.com';
  const pageUrl = `${appUrl}/products/${product.slug}`;

  return {
    title: `${product.title} | Instant PDF Access`,
    description: product.description,
    alternates: {
      canonical: pageUrl,
    },
    openGraph: {
      title: product.title,
      description: product.description,
      url: pageUrl,
      type: 'book',
      images: [
        {
          url: `${appUrl}${product.coverImage}`,
          width: 800,
          height: 1200,
          alt: product.title,
        },
      ],
    },
  };
}

export default function ProductDetailPage({ params }: ProductPageProps) {
  const product = getProductBySlug(params.slug);
  if (!product) {
    notFound();
  }

  // Schema.org Structured Data for Products & Offers
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.title,
    description: product.description,
    image: `https://academiccomeback.com${product.coverImage}`,
    offers: {
      '@type': 'Offer',
      price: product.priceNaira.toString(),
      priceCurrency: 'NGN',
      availability: 'https://schema.org/InStock',
      url: `https://academiccomeback.com/products/${product.slug}`,
      priceValidUntil: '2027-01-01',
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <ProductClientView product={product} />
    </>
  );
}
