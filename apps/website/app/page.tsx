'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { CANONICAL_PRODUCTS } from '@/lib/products';
import { Product } from '@repo/api-contracts';
import CheckoutModal from '@/components/checkout/CheckoutModal';
import {
  Sparkles,
  BookOpen,
  CheckCircle,
  Zap,
  ArrowRight,
  Shield,
  Clock,
  Download,
  Users,
} from 'lucide-react';

export default function HomePage() {
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const academicPackage = CANONICAL_PRODUCTS.find((p) => p.slug === 'academic-comeback-package')!;
  const otherProducts = CANONICAL_PRODUCTS.filter((p) => p.slug !== 'academic-comeback-package');

  const openCheckout = (prod: Product) => {
    setSelectedProduct(prod);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-24">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="text-center space-y-6 max-w-3xl mx-auto">
          {/* Promo Tag */}
          <div className="inline-flex items-center gap-2 bg-[#d4af37]/15 border border-[#d4af37]/40 px-4 py-1.5 rounded-full text-xs font-bold text-[#f3e5ab] tracking-wider uppercase animate-pulse">
            <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
            Active Promotional Pricing &bull; Save 75%
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-6xl font-black text-white tracking-tight leading-[1.15]">
            The Blueprint to Rescue Your Grades &amp; Build{' '}
            <span className="gold-gradient-text">Unfair Cognitive Leverage</span>
          </h1>

          {/* Subhead */}
          <p className="text-slate-300 text-base sm:text-lg leading-relaxed max-w-2xl mx-auto">
            Stop grinding 8 hours a day for mediocre exam scores. Deploy high-yield active recall systems, 14-day course deconstruction, and elite study protocols used by first-class students across Nigeria.
          </p>

          {/* Featured Offer Card */}
          <div className="bg-[#131b2e] border-2 border-[#d4af37]/40 rounded-2xl p-6 sm:p-8 max-w-xl mx-auto text-left shadow-2xl space-y-6 mt-8">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[11px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-2.5 py-1 rounded">
                  7-in-1 Complete System
                </span>
                <h3 className="text-xl sm:text-2xl font-black text-white mt-2">
                  The Academic Comeback Package
                </h3>
              </div>
              <div className="text-right">
                <span className="text-3xl font-black text-[#d4af37]">₦5,000</span>
                <span className="text-xs text-slate-500 line-through block">₦20,000</span>
              </div>
            </div>

            <ul className="space-y-2.5 text-xs sm:text-sm text-slate-300">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>The 7 Complete Masterclass Books</strong> (Instant PDF Download)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>Active Recall Study Tracker Templates</strong> (Google Sheets &amp; Notion)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span><strong>52-Week Academic Mastery Email Drip</strong> (Automated Sunday Masterclasses)</span>
              </li>
            </ul>

            <button
              onClick={() => openCheckout(academicPackage)}
              className="w-full gold-btn py-4 rounded-xl font-black text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-xl"
            >
              <Zap className="w-4 h-4 fill-current" /> Download Complete Package for ₦5,000 &rarr;
            </button>

            <div className="flex items-center justify-center gap-6 text-[11px] text-slate-400 pt-1">
              <span className="flex items-center gap-1"><Download className="w-3.5 h-3.5 text-[#d4af37]" /> Instant Digital Access</span>
              <span className="flex items-center gap-1"><Shield className="w-3.5 h-3.5 text-emerald-400" /> Guaranteed DRM-Free PDF</span>
            </div>
          </div>
        </div>
      </section>

      {/* Complete Books Catalogue */}
      <section id="products" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <span className="text-xs font-bold text-[#d4af37] uppercase tracking-widest">
            Tactical Digital Publishing
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white">
            Individual Masterclasses &amp; Field Manuals
          </h2>
          <p className="text-sm text-slate-400">
            Every book solves one high-friction life, career, or habit bottleneck with zero fluff and exact execution protocols.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {otherProducts.map((prod) => (
            <div
              key={prod.id}
              className="bg-[#131b2e] border border-[#d4af37]/20 rounded-2xl p-6 flex flex-col justify-between hover:border-[#d4af37]/50 transition duration-300 shadow-lg group"
            >
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <span className="text-[10px] uppercase font-bold text-[#f3e5ab] bg-[#d4af37]/10 px-2 py-0.5 rounded">
                    {prod.category}
                  </span>
                  <div className="text-right">
                    <span className="text-lg font-black text-[#d4af37]">₦{prod.priceNaira.toLocaleString()}</span>
                    <span className="text-xs text-slate-500 line-through block">₦{prod.regularPriceNaira.toLocaleString()}</span>
                  </div>
                </div>

                <h3 className="text-lg font-bold text-white group-hover:text-[#f3e5ab] transition">
                  <Link href={`/products/${prod.slug}`}>{prod.title}</Link>
                </h3>

                <p className="text-xs text-slate-300 line-clamp-3 leading-relaxed">
                  {prod.description}
                </p>

                <div className="pt-2 border-t border-slate-800">
                  <span className="text-[11px] font-semibold text-slate-400 block mb-1.5">Key Outcomes:</span>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {prod.benefits.slice(0, 2).map((b, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <span className="line-clamp-1">{b}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="pt-6 flex gap-3">
                <Link
                  href={`/products/${prod.slug}`}
                  className="flex-1 text-center py-2.5 px-3 bg-[#1e293b] hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition"
                >
                  View Details
                </Link>
                <button
                  onClick={() => openCheckout(prod)}
                  className="flex-1 gold-btn py-2.5 px-3 rounded-lg text-xs font-bold uppercase transition"
                >
                  Buy (₦5,000)
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* The Hormozi Value Stack */}
      <section className="bg-gradient-to-b from-[#131b2e] to-[#0b0f19] border-y border-[#d4af37]/20 py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto space-y-10">
          <div className="text-center space-y-3">
            <span className="text-xs font-bold text-[#d4af37] uppercase tracking-widest">
              The Value Equation
            </span>
            <h2 className="text-3xl font-extrabold text-white">Why This Outperforms 100 Hours of Blind Studying</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-[#0b0f19] p-6 rounded-xl border border-slate-800 space-y-2">
              <div className="text-[#d4af37] font-bold text-sm">1. Dream Outcome</div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Graduate with first-class honors, conquer dense mathematical exams effortlessly, and build income skills while in university.
              </p>
            </div>
            <div className="bg-[#0b0f19] p-6 rounded-xl border border-slate-800 space-y-2">
              <div className="text-[#d4af37] font-bold text-sm">2. Perceived Likelihood of Success</div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Tested across hundreds of Nigerian university students in UNILAG, UI, FUTA, UNN, and OAU with verifiable grade jumps within one semester.
              </p>
            </div>
            <div className="bg-[#0b0f19] p-6 rounded-xl border border-slate-800 space-y-2">
              <div className="text-[#d4af37] font-bold text-sm">3. Time Delay: Near Zero</div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Instant delivery directly to your phone. You can read Chapter 1 of any manual and execute its protocol tonight before sleeping.
              </p>
            </div>
            <div className="bg-[#0b0f19] p-6 rounded-xl border border-slate-800 space-y-2">
              <div className="text-[#d4af37] font-bold text-sm">4. Effort &amp; Sacrifice: Minimized</div>
              <p className="text-xs text-slate-300 leading-relaxed">
                No 400-page academic fluff. Every manual is under 70 concise pages with copy-paste templates, eliminating wasted study time.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Checkout Modal */}
      {selectedProduct && (
        <CheckoutModal
          product={selectedProduct}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </div>
  );
}
