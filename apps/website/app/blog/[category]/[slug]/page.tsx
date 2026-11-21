import React from 'react';
import { Metadata } from 'next';
import Link from 'next/link';
import fs from 'fs';
import path from 'path';
import { notFound } from 'next/navigation';
import { ArrowLeft, Clock, Calendar, BookOpen, HelpCircle } from 'lucide-react';

interface BlogPostPageProps {
  params: { category: string; slug: string };
}

interface BlogPostData {
  slug: string;
  category: string;
  categoryName: string;
  title: string;
  description: string;
  canonical: string;
  image: string;
  datePublished: string;
  dateModified: string;
  author: string;
  readingTime: string;
  faqs: Array<{ question: string; answer: string }>;
  contentHtml: string;
}

function getPost(category: string, slug: string): BlogPostData | null {
  try {
    const filePath = path.join(process.cwd(), 'data', 'blog', 'posts', category, `${slug}.json`);
    if (!fs.existsSync(filePath)) {
      return null;
    }
    const raw = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export async function generateStaticParams() {
  try {
    const manifestPath = path.join(process.cwd(), 'data', 'blog', 'manifest.json');
    if (!fs.existsSync(manifestPath)) {
      return [];
    }
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
    // Pre-generate the top 30 most popular articles at build time; others generate on-demand via ISR
    return manifest.slice(0, 30).map((post: { category: string; slug: string }) => ({
      category: post.category,
      slug: post.slug,
    }));
  } catch {
    return [];
  }
}

export async function generateMetadata({ params }: BlogPostPageProps): Promise<Metadata> {
  const post = getPost(params.category, params.slug);
  const formattedTitle = post
    ? post.title
    : params.slug
        .split('-')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://academiccomeback.com';
  const canonicalUrl = `${appUrl}/blog/${params.category}/${params.slug}`;

  return {
    title: `${formattedTitle} | Academic Comeback`,
    description: post?.description || `Tactical academic study guide on ${formattedTitle.toLowerCase()}. Tested protocols for Nigerian university undergraduates and high-performers.`,
    alternates: {
      canonical: canonicalUrl,
    },
    openGraph: {
      title: formattedTitle,
      description: post?.description || `Tactical academic study guide on ${formattedTitle.toLowerCase()}.`,
      url: canonicalUrl,
      type: 'article',
      images: [
        {
          url: post?.image || `${appUrl}/assets/images/blog/${params.slug}.webp`,
          width: 1200,
          height: 630,
          alt: formattedTitle,
        },
      ],
    },
  };
}

export default function BlogPostPage({ params }: BlogPostPageProps) {
  const post = getPost(params.category, params.slug);

  const title = post
    ? post.title
    : params.slug
        .split('-')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');

  const categoryName = post
    ? post.categoryName
    : params.category
        .split('-')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://academiccomeback.com';
  const canonicalUrl = `${appUrl}/blog/${params.category}/${params.slug}`;

  const jsonLdGraph: any[] = [
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        {
          '@type': 'ListItem',
          position: 1,
          name: 'Home',
          item: appUrl,
        },
        {
          '@type': 'ListItem',
          position: 2,
          name: 'Blog',
          item: `${appUrl}/blog`,
        },
        {
          '@type': 'ListItem',
          position: 3,
          name: categoryName,
          item: `${appUrl}/blog/${params.category}`,
        },
        {
          '@type': 'ListItem',
          position: 4,
          name: title,
          item: canonicalUrl,
        },
      ],
    },
    {
      '@type': 'BlogPosting',
      headline: title,
      description: post?.description || '',
      datePublished: post?.datePublished || '2026-09-26T08:00:00+01:00',
      dateModified: post?.dateModified || '2026-09-26T08:00:00+01:00',
      author: {
        '@type': 'Person',
        name: post?.author || 'David Itoya',
      },
      publisher: {
        '@type': 'Organization',
        name: 'Scale Group Publishing',
        logo: {
          '@type': 'ImageObject',
          url: `${appUrl}/assets/images/logo.png`,
        },
      },
      mainEntityOfPage: canonicalUrl,
    },
  ];

  if (post?.faqs && post.faqs.length > 0) {
    jsonLdGraph.push({
      '@type': 'FAQPage',
      mainEntity: post.faqs.map((f) => ({
        '@type': 'Question',
        name: f.question,
        acceptedAnswer: {
          '@type': 'Answer',
          text: f.answer,
        },
      })),
    });
  }

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': jsonLdGraph,
  };

  return (
    <article className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Breadcrumb Navigation */}
      <nav className="flex items-center space-x-2 text-xs text-slate-400">
        <Link href="/" className="hover:text-white transition">Home</Link>
        <span>/</span>
        <span className="text-[#d4af37]">{categoryName}</span>
        <span>/</span>
        <span className="text-slate-300 truncate max-w-xs">{title}</span>
      </nav>

      {/* Article Header */}
      <header className="space-y-4 border-b border-slate-800 pb-8">
        <span className="text-[11px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-2.5 py-1 rounded inline-block">
          {categoryName}
        </span>
        <h1 className="text-3xl sm:text-5xl font-black text-white leading-tight">
          {title}
        </h1>
        <div className="flex items-center gap-6 text-xs text-slate-400 pt-2">
          <span className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5" /> Published by {post?.author || 'David Itoya'}
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" /> {post?.readingTime || '6 min read'}
          </span>
        </div>
      </header>

      {/* Article Content */}
      <div className="prose prose-invert prose-gold max-w-none space-y-6 text-slate-300 leading-relaxed text-sm sm:text-base">
        {post?.contentHtml ? (
          <div dangerouslySetInnerHTML={{ __html: post.contentHtml }} />
        ) : (
          <p className="text-base sm:text-lg font-medium text-slate-200">
            Most students spend hours rereading highlighted textbooks, hoping passive exposure converts into exam retention. In Nigerian university lecture halls, where exams are heavily concept-dense and graded with strict marking schemes, passive study is the fastest route to exhaustion without results.
          </p>
        )}

        {/* Tactical Offer Banner */}
        <div className="bg-[#131b2e] border-2 border-[#d4af37]/40 rounded-2xl p-6 sm:p-8 my-8 space-y-4 not-prose">
          <span className="text-[10px] uppercase font-bold tracking-widest text-[#d4af37] bg-[#d4af37]/10 px-2 py-0.5 rounded">
            Recommended Study System
          </span>
          <h3 className="text-xl font-bold text-white">The Academic Comeback Package (7-in-1 Study System)</h3>
          <p className="text-xs sm:text-sm text-slate-300">
            If you want the complete, step-by-step active recall spreadsheets and 14-day exam cramming protocols mentioned in this guide, access the complete manual below.
          </p>
          <div className="flex items-center justify-between pt-2">
            <div>
              <span className="text-xl font-black text-[#d4af37]">₦5,000</span>
              <span className="text-xs text-slate-400 line-through ml-2">₦20,000</span>
            </div>
            <Link
              href="/products/academic-comeback-package"
              className="gold-btn py-2.5 px-4 rounded-lg text-xs font-bold uppercase"
            >
              Get The Package (₦5,000) &rarr;
            </Link>
          </div>
        </div>

        {/* Frequently Asked Questions */}
        {post?.faqs && post.faqs.length > 0 && (
          <section className="mt-12 pt-8 border-t border-slate-800 space-y-6 not-prose">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <HelpCircle className="w-5 h-5 text-[#d4af37]" />
              Frequently Asked Questions
            </h3>
            <div className="space-y-4">
              {post.faqs.map((faq, idx) => (
                <div key={idx} className="bg-[#131b2e]/60 border border-slate-800 rounded-xl p-5 space-y-2">
                  <h4 className="text-sm sm:text-base font-semibold text-white">
                    {faq.question}
                  </h4>
                  <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                    {faq.answer}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </article>
  );
}
