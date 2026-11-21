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
} from 'lucide-react';

export default function ProductClientView({ product }: { product: Product }) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-20 space-y-12">
      {/* Back Link */}
      <Link
        href="/#products"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-[#d4af37] transition"
      >
        <ArrowLeft className="w-4 h-4" /> Back to All Books &amp; Masterclasses
      </Link>

      {/* Main Product Card */}
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
          </div>

          <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
            {product.description}
          </p>

          {/* Key Deliverables Stack */}
          <div className="bg-[#0b0f19] border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-xs font-bold text-[#f3e5ab] uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" /> Core Outcomes &amp; Systems:
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
              Included In Your Download:
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

      {/* Checkout Modal */}
      <CheckoutModal
        product={product}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
