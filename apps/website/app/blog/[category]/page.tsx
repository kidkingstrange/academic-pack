import React from 'react';
import { Metadata } from 'next';
import Link from 'next/link';
import fs from 'fs';
import path from 'path';
import { notFound } from 'next/navigation';
import { ArrowLeft, ArrowRight, Clock, BookOpen } from 'lucide-react';

interface CategoryPageProps {
  params: { category: string };
}

const CATEGORY_MAP: Record<string, { title: string; description: string }> = {
  academics: {
    title: 'Academics & High-Yield Study Systems',
    description:
      'Master active recall, spaced repetition, 14-day exam cramming frameworks, CGPA calculation, and past question analysis.',
  },
  'balancing-work-and-school': {
    title: 'Balancing Work & School',
    description:
      'Tactical guides for student freelancers, remote contractors, campus businesses, and night-shift workers keeping their GPAs high.',
  },
  finances: {
    title: 'Student Finances & Budgeting',
    description:
      'Survive food inflation, manage monthly allowances, avoid financial distress, and master smart campus money management.',
  },
  'hostel-and-accommodation': {
    title: 'Hostel & Off-Campus Living',
    description:
      'Roommate conflict resolution, electricity and water scarcity protocols, landlord negotiation, and personal security.',
  },
  'mental-health': {
    title: 'Mental Health & Academic Stamina',
    description:
      'Combat exam anxiety, academic burnout, parental pressure, ASUU strike uncertainty, and recover emotional resilience.',
  },
};

export async function generateStaticParams() {
  return Object.keys(CATEGORY_MAP).map((category) => ({ category }));
}

export async function generateMetadata({ params }: CategoryPageProps): Promise<Metadata> {
  const cat = CATEGORY_MAP[params.category];
  if (!cat) {
    return { title: 'Category Not Found' };
  }

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://academiccomeback.com';
  const canonicalUrl = `${appUrl}/blog/${params.category}`;

  return {
    title: `${cat.title} | Academic Comeback Guides`,
    description: cat.description,
    alternates: {
      canonical: canonicalUrl,
    },
    openGraph: {
      title: cat.title,
      description: cat.description,
      url: canonicalUrl,
      type: 'website',
    },
  };
}

export default function CategoryPage({ params }: CategoryPageProps) {
  const catInfo = CATEGORY_MAP[params.category];
  if (!catInfo) {
    notFound();
  }

  let categoryPosts: any[] = [];
  try {
    const manifestPath = path.join(process.cwd(), 'data', 'blog', 'manifest.json');
    if (fs.existsSync(manifestPath)) {
      const allPosts = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
      categoryPosts = allPosts.filter((p: any) => p.category === params.category);
    }
  } catch (err) {
    console.error('Error loading posts for category:', err);
  }

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://academiccomeback.com';
  const canonicalUrl = `${appUrl}/blog/${params.category}`;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: catInfo.title,
    description: catInfo.description,
    url: canonicalUrl,
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: categoryPosts.map((post, idx) => ({
        '@type': 'ListItem',
        position: idx + 1,
        url: `${appUrl}/blog/${post.category}/${post.slug}`,
        name: post.title,
      })),
    },
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Breadcrumb Navigation */}
      <nav className="flex items-center space-x-2 text-xs text-slate-400">
        <Link href="/" className="hover:text-white transition">Home</Link>
        <span>/</span>
        <Link href="/blog" className="hover:text-white transition">Blog</Link>
        <span>/</span>
        <span className="text-[#d4af37] font-semibold">{catInfo.title}</span>
      </nav>

      {/* Category Header */}
      <header className="space-y-4 max-w-3xl">
        <span className="text-[11px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-3 py-1 rounded-full inline-block">
          Topic Hub
        </span>
        <h1 className="text-3xl sm:text-5xl font-black text-white">
          {catInfo.title}
        </h1>
        <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
          {catInfo.description}
        </p>
        <p className="text-xs text-slate-400">
          Showing <strong>{categoryPosts.length}</strong> tactical guides in this category.
        </p>
      </header>

      {/* Posts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-4">
        {categoryPosts.map((post) => (
          <Link
            key={post.slug}
            href={`/blog/${post.category}/${post.slug}`}
            className="bg-[#131b2e]/60 hover:bg-[#131b2e] border border-slate-800/80 hover:border-[#d4af37]/40 rounded-2xl p-6 transition duration-200 flex flex-col justify-between group"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#d4af37] uppercase tracking-wider bg-[#d4af37]/10 px-2 py-0.5 rounded">
                  {post.categoryName}
                </span>
                <span className="text-[11px] text-slate-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" /> {post.readingTime}
                </span>
              </div>

              <h2 className="text-lg font-bold text-white group-hover:text-[#d4af37] transition leading-snug line-clamp-2">
                {post.title}
              </h2>

              <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">
                {post.description}
              </p>
            </div>

            <div className="pt-6 border-t border-slate-800/60 mt-6 flex items-center justify-between text-xs font-semibold text-slate-300 group-hover:text-[#d4af37]">
              <span>Read Guide</span>
              <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition" />
            </div>
          </Link>
        ))}
      </div>

      {/* Back to all blogs CTA */}
      <div className="pt-8 text-center">
        <Link
          href="/blog"
          className="inline-flex items-center gap-2 text-xs font-bold text-[#d4af37] hover:underline"
        >
          <ArrowLeft className="w-4 h-4" /> Back to all 201+ Guides
        </Link>
      </div>
    </div>
  );
}
