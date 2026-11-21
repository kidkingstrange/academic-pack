'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { Search, Clock, BookOpen, ArrowRight, Sparkles, Filter } from 'lucide-react';

interface ManifestPost {
  slug: string;
  category: string;
  categoryName: string;
  title: string;
  description: string;
  readingTime: string;
  datePublished: string;
}

interface BlogIndexClientProps {
  posts: ManifestPost[];
}

const CATEGORIES = [
  { id: 'all', name: 'All Guides' },
  { id: 'academics', name: 'Academics & GPA' },
  { id: 'balancing-work-and-school', name: 'Work & School' },
  { id: 'finances', name: 'Student Finances' },
  { id: 'hostel-and-accommodation', name: 'Hostel & Living' },
  { id: 'mental-health', name: 'Mental Health' },
];

export default function BlogIndexClient({ posts }: BlogIndexClientProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const filteredPosts = useMemo(() => {
    return posts.filter((post) => {
      const matchesCategory =
        selectedCategory === 'all' || post.category === selectedCategory;
      const matchesSearch =
        searchQuery.trim() === '' ||
        post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        post.description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [posts, selectedCategory, searchQuery]);

  return (
    <div className="space-y-12">
      {/* Search & Category Filter Toolbar */}
      <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search 201+ study protocols, exam cramming plans, CGPA guides..."
            className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl pl-12 pr-4 py-3.5 text-white placeholder-slate-500 focus:outline-none focus:border-[#d4af37] text-sm"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-white"
            >
              Clear
            </button>
          )}
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                selectedCategory === cat.id
                  ? 'bg-[#d4af37] text-black font-bold shadow-md'
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-1">
        <span>
          Showing <strong className="text-white">{filteredPosts.length}</strong> of{' '}
          <strong className="text-white">{posts.length}</strong> tactical guides
        </span>
        {selectedCategory !== 'all' && (
          <button
            onClick={() => setSelectedCategory('all')}
            className="text-[#d4af37] hover:underline"
          >
            Reset filter
          </button>
        )}
      </div>

      {/* Articles Grid */}
      {filteredPosts.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPosts.map((post) => (
            <Link
              key={`${post.category}-${post.slug}`}
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
                <span>Read Full Guide</span>
                <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition" />
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-12 text-center space-y-4">
          <BookOpen className="w-12 h-12 text-slate-500 mx-auto" />
          <h3 className="text-lg font-bold text-white">No guides found</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            No guides match &ldquo;{searchQuery}&rdquo;. Try searching for &ldquo;active recall&rdquo;, &ldquo;cramming&rdquo;, &ldquo;100 level&rdquo;, or reset your category filter.
          </p>
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedCategory('all');
            }}
            className="gold-btn py-2 px-4 rounded-lg text-xs font-bold"
          >
            View All Guides
          </button>
        </div>
      )}

      {/* Flagship Promotional Banner */}
      <div className="bg-gradient-to-r from-[#131b2e] to-[#1c2742] border-2 border-[#d4af37]/40 rounded-3xl p-8 sm:p-12 text-center space-y-6">
        <span className="text-[11px] font-extrabold uppercase tracking-widest text-[#d4af37] bg-[#d4af37]/10 px-3 py-1 rounded-full inline-flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5" /> High-Performance Study System
        </span>
        <h2 className="text-3xl sm:text-4xl font-black text-white">
          Stop Studying Harder. Start Studying Structurally.
        </h2>
        <p className="text-sm sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">
          The Academic Comeback Package contains the complete 7-in-1 system: Active Recall Notion templates, 14-day cramming battleplans, and mental stamina protocols verified by top university graduates.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
          <Link
            href="/products/academic-comeback-package"
            className="gold-btn py-3.5 px-8 rounded-xl text-sm font-bold uppercase tracking-wider"
          >
            Claim The 7-in-1 Package (₦5,000) &rarr;
          </Link>
          <Link
            href="/library"
            className="bg-slate-800 hover:bg-slate-700 text-white py-3.5 px-6 rounded-xl text-sm font-semibold transition"
          >
            Access My Library
          </Link>
        </div>
      </div>
    </div>
  );
}
