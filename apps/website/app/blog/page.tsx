import React from 'react';
import { Metadata } from 'next';
import fs from 'fs';
import path from 'path';
import BlogIndexClient from './BlogIndexClient';

export const metadata: Metadata = {
  title: '201+ Free Tactical University Guides & Study Protocols | Academic Comeback',
  description:
    'Comprehensive library of 201+ evidence-based study systems, active recall tactics, hostel survival protocols, student finance blueprints, and mental resilience guides for undergraduates.',
  alternates: {
    canonical: 'https://academiccomeback.com/blog',
  },
  openGraph: {
    title: '201+ Free Tactical University Guides & Study Protocols',
    description:
      'Comprehensive library of 201+ evidence-based study systems, active recall tactics, hostel survival protocols, and student finance blueprints.',
    url: 'https://academiccomeback.com/blog',
    type: 'website',
  },
};

export default function BlogIndexPage() {
  let posts = [];
  try {
    const manifestPath = path.join(process.cwd(), 'data', 'blog', 'manifest.json');
    if (fs.existsSync(manifestPath)) {
      posts = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
    }
  } catch (err) {
    console.error('Failed to load blog manifest:', err);
  }

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: '201+ Free Tactical University Guides & Study Protocols',
    description:
      'Comprehensive library of 201+ evidence-based study systems and student survival guides.',
    url: 'https://academiccomeback.com/blog',
    publisher: {
      '@type': 'Organization',
      name: 'Academic Comeback',
      logo: {
        '@type': 'ImageObject',
        url: 'https://academiccomeback.com/assets/images/logo.png',
      },
    },
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Page Header */}
      <header className="space-y-4 text-center max-w-3xl mx-auto">
        <span className="text-[11px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-3 py-1 rounded-full inline-block">
          Open-Access Knowledge Base
        </span>
        <h1 className="text-3xl sm:text-5xl font-black text-white tracking-tight">
          Tactical Campus Guides &amp; Systems
        </h1>
        <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
          Over 200 battle-tested guides covering university exam preparation, CGPA recovery, memory systems, student budgeting, and mental stamina under academic pressure.
        </p>
      </header>

      {/* Interactive Client Search & Filter */}
      <BlogIndexClient posts={posts} />
    </div>
  );
}
