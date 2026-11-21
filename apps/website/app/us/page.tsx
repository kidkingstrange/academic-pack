import React from 'react';
import { Metadata } from 'next';
import USClientView from './USClientView';

export const metadata: Metadata = {
  title: 'Academic Comeback Package — US & International Edition ($15)',
  description:
    'Evidence-based learning frameworks for US premeds, nursing candidates (NCLEX), law students (LSAT), and university undergraduates. Cut study time in half today.',
  alternates: {
    canonical: 'https://academiccomeback.com/us',
  },
  openGraph: {
    title: 'Academic Comeback Package — US & International Edition ($15)',
    description:
      'Master evidence-based active recall and cognitive acceleration systems built for MCAT, USMLE, NCLEX, LSAT, CPA, GRE & college exams.',
    url: 'https://academiccomeback.com/us',
    type: 'website',
  },
};

export default function USPage() {
  const jsonLd = {
    '@context': 'https://schema.org/',
    '@type': 'Product',
    name: 'Academic Comeback Package (US & International Edition)',
    image: 'https://academiccomeback.com/assets/images/bookcover.webp',
    description:
      'A comprehensive 7-part study system grounded in cognitive psychology and active recall for American students and professionals.',
    brand: {
      '@type': 'Brand',
      name: 'Academic Comeback',
    },
    offers: {
      '@type': 'Offer',
      price: '15.00',
      priceCurrency: 'USD',
      availability: 'https://schema.org/InStock',
      url: 'https://academiccomeback.com/us',
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <USClientView />
    </>
  );
}
