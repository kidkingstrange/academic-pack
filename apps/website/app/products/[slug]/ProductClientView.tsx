'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Product } from '@repo/api-contracts';
import CheckoutModal from '@/components/checkout/CheckoutModal';
import {
  CheckCircle,
  ShieldCheck,
  Zap,
  Download,
  BookOpen,
  ArrowLeft,
  Sparkles,
  AlertTriangle,
  HelpCircle,
  XCircle,
  Award
} from 'lucide-react';

export default function ProductClientView({ product }: { product: Product }) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-24 space-y-16">
      {/* Back Link */}
      <Link
        href="/#products"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-[#d4af37] transition"
      >
        <ArrowLeft className="w-4 h-4" /> Back to All Books &amp; Masterclasses
      </Link>

      {/* Hero / Main Overview Card */}
      <div className="bg-[#131b2e] border border-[#d4af37]/30 rounded-3xl p-6 sm:p-10 shadow-2xl grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        {/* Left Column: Details */}
        <div className="md:col-span-7 space-y-6">
          <div className="space-y-2">
            <span className="text-[11px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-2.5 py-1 rounded inline-block">
              {product.category}
            </span>
            <h1 className="text-2xl sm:text-4xl font-black text-white leading-tight">
              {product.title}
            </h1>
            {product.tagline && (
              <p className="text-sm font-semibold text-[#f3e5ab]">
                {product.tagline}
              </p>
            )}
          </div>

          <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
            {product.description}
          </p>

          {/* Key Deliverables Stack */}
          <div className="bg-[#0b0f19] border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-xs font-bold text-[#f3e5ab] uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" /> Core Outcomes &amp; Breakthroughs:
            </h3>
            <ul className="space-y-2 text-xs sm:text-sm text-slate-300">
              {product.benefits.map((b, i) => (
                <li key={i} className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* What Is Included */}
          <div className="space-y-2 pt-2">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Included In Your Digital Package:
            </h3>
            <ul className="space-y-1.5 text-xs text-slate-300">
              {product.features.map((f, i) => (
                <li key={i} className="flex items-center gap-2">
                  <BookOpen className="w-3.5 h-3.5 text-[#d4af37] shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right Column: Pricing & Checkout Box */}
        <div className="md:col-span-5 bg-[#0b0f19] border-2 border-[#d4af37]/40 rounded-2xl p-6 space-y-6 shadow-xl sticky top-24">
          <div className="flex justify-between items-baseline border-b border-slate-800 pb-4">
            <div>
              <span className="text-xs text-slate-400 block font-medium">Promotional Price:</span>
              <span className="text-3xl font-black text-[#d4af37]">₦{product.priceNaira.toLocaleString()}</span>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-400 line-through">₦{product.regularPriceNaira.toLocaleString()}</span>
              <span className="text-[10px] text-emerald-400 font-bold block">SAVE 75%</span>
            </div>
          </div>

          <div className="space-y-3 text-xs text-slate-300">
            <div className="flex items-center gap-2">
              <Download className="w-4 h-4 text-[#d4af37]" />
              <span>Instant PDF delivery on mobile &amp; laptop</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Permanent reading access in student library</span>
            </div>
          </div>

          <button
            onClick={() => setIsModalOpen(true)}
            className="w-full gold-btn py-4 rounded-xl font-black text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-xl"
          >
            <Zap className="w-4 h-4 fill-current" /> Buy Now (₦{product.priceNaira.toLocaleString()})
          </button>

          <p className="text-[11px] text-center text-slate-400">
            🔒 Processed securely with Paystack &amp; Flutterwave. 256-bit SSL encryption.
          </p>
        </div>
      </div>

      {/* Pain Agitation Section (if defined) */}
      {product.painPoints && product.painPoints.length > 0 && (
        <section className="bg-[#131b2e]/60 border border-slate-800 rounded-3xl p-6 sm:p-10 space-y-6">
          <div className="text-center space-y-2 max-w-2xl mx-auto">
            <span className="text-[10px] uppercase font-bold tracking-widest text-rose-400 bg-rose-500/10 px-2.5 py-1 rounded-full">
              Sound Familiar?
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-white">
              The Invisible Cycle Holding You Back
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
              If you have experienced two or more of these symptoms, you are not lazy or broken — you are trapped in an unengineered behavioral loop.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
            {product.painPoints.map((pain, idx) => (
              <div key={idx} className="bg-[#0b0f19] border border-slate-800/80 rounded-xl p-4 flex items-start gap-3">
                <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <span className="text-xs sm:text-sm text-slate-300 leading-relaxed">{pain}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Detailed Chapters Breakdown (if defined) */}
      {product.chapters && product.chapters.length > 0 && (
        <section className="space-y-8">
          <div className="text-center space-y-2 max-w-2xl mx-auto">
            <span className="text-[10px] uppercase font-bold tracking-widest text-[#d4af37] bg-[#d4af37]/10 px-2.5 py-1 rounded-full">
              Full Masterclass Curriculum
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-white">
              Inside The Complete Operating Manual
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {product.chapters.map((ch, idx) => (
              <div
                key={idx}
                className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-[#d4af37] bg-[#d4af37]/10 px-2 py-0.5 rounded">
                    Chapter {ch.number}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white">{ch.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{ch.summary}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* FAQ Section (if defined) */}
      {product.faqs && product.faqs.length > 0 && (
        <section className="bg-[#131b2e] border border-slate-800 rounded-3xl p-6 sm:p-10 space-y-6">
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-[#d4af37]" />
            Frequently Asked Questions
          </h3>
          <div className="space-y-4">
            {product.faqs.map((faq, idx) => (
              <div key={idx} className="bg-[#0b0f19] border border-slate-800 rounded-xl p-5 space-y-2">
                <h4 className="text-sm font-semibold text-white">{faq.question}</h4>
                <p className="text-xs text-slate-300 leading-relaxed">{faq.answer}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Final Bottom Call to Action */}
      <div className="bg-gradient-to-r from-[#131b2e] to-[#1c2742] border-2 border-[#d4af37]/40 rounded-3xl p-8 sm:p-12 text-center space-y-6">
        <h2 className="text-3xl sm:text-4xl font-black text-white">
          Begin Your Turnaround Today
        </h2>
        <p className="text-xs sm:text-sm text-slate-300 max-w-xl mx-auto leading-relaxed">
          Immediate download delivery with lifetime library updates. Protected by our 100% money back guarantee.
        </p>
        <button
          onClick={() => setIsModalOpen(true)}
          className="gold-btn py-4 px-10 rounded-xl text-sm font-bold uppercase tracking-wider"
        >
          Claim For ₦{product.priceNaira.toLocaleString()} &rarr;
        </button>
      </div>

      {/* Checkout Modal */}
      <CheckoutModal
        product={product}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
