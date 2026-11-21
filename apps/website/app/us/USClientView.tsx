'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import CheckoutModal from '@/components/checkout/CheckoutModal';
import {
  CheckCircle2,
  ShieldCheck,
  Star,
  Clock,
  Sparkles,
  BookOpen,
  ArrowRight,
  GraduationCap,
  Globe2,
  Check
} from 'lucide-react';

export default function USClientView() {
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);

  const modules = [
    {
      title: 'Phase 1: Cognitive Active Recall Architecture',
      desc: 'Ditch passive re-reading. Implement the retrieval-cue spreadsheet protocol that forces high-density neuroplastic encoding in half the time.',
    },
    {
      title: 'Phase 2: High-Yield Spaced Repetition Scheduling',
      desc: 'Algorithmically timed review intervals engineered for 500+ page curricula across physiology, organic chemistry, pathology, and statutes.',
    },
    {
      title: 'Phase 3: The 14-Day Exam Panic Cramming Matrix',
      desc: 'When deadlines compress, execute this hour-by-hour triage battleplan to salvage passing or honors-level scores in record time.',
    },
    {
      title: 'Phase 4: Mental Stamina & Blackout Reversal',
      desc: 'Neurological grounding protocols to prevent exam-hall amygdala hijack, brain fog, and panic blanks under intense proctoring.',
    },
    {
      title: 'Phase 5: Notion & Anki Automated Study Vaults',
      desc: 'Pre-formatted, turnkey workspace templates ready to clone with one click for effortless concept organization.',
    },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-16">
      {/* Hero Header */}
      <div className="text-center space-y-6 max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 bg-[#d4af37]/10 border border-[#d4af37]/30 px-3.5 py-1.5 rounded-full text-xs font-bold text-[#d4af37]">
          <Globe2 className="w-4 h-4" /> US &amp; INTERNATIONAL EDITION • $15 PROMO
        </div>

        <h1 className="text-4xl sm:text-6xl font-black text-white leading-tight tracking-tight">
          Stop Studying Harder.{' '}
          <span className="text-[#d4af37]">Start Learning Smarter.</span>
        </h1>

        <p className="text-base sm:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed">
          The comprehensive 7-part digital learning system built for US pre-meds, nursing candidates (NCLEX), law students (LSAT), and university undergraduates who need to retain complex information fast.
        </p>

        {/* Pricing Card Header */}
        <div className="pt-2">
          <div className="inline-flex items-baseline gap-3 bg-[#131b2e] border-2 border-[#d4af37]/40 rounded-2xl px-6 py-4 shadow-2xl">
            <span className="text-4xl sm:text-5xl font-black text-[#d4af37]">$15</span>
            <span className="text-sm sm:text-base text-slate-400 line-through">$47 USD</span>
            <span className="text-xs uppercase font-extrabold bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded">
              Save 68% Today
            </span>
          </div>
        </div>

        <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={() => setIsCheckoutOpen(true)}
            className="w-full sm:w-auto gold-btn py-4 px-10 rounded-xl text-sm font-bold uppercase tracking-wider shadow-lg flex items-center justify-center gap-2"
          >
            Get Instant Digital Access ($15) &rarr;
          </button>
          <Link
            href="/library"
            className="w-full sm:w-auto bg-slate-800 hover:bg-slate-700 text-white py-4 px-8 rounded-xl text-sm font-semibold transition"
          >
            Access My Library
          </Link>
        </div>

        <p className="text-xs text-slate-400 flex items-center justify-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          Instant PDF delivery • Secure Card Checkout • 60-Day Money Back Guarantee
        </p>
      </div>

      {/* Social Proof Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 text-center">
        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-1">
          <div className="text-2xl sm:text-3xl font-black text-[#d4af37]">4.9 / 5.0</div>
          <p className="text-xs text-slate-400">Average Student Rating</p>
        </div>
        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-1">
          <div className="text-2xl sm:text-3xl font-black text-white">50% Cut</div>
          <p className="text-xs text-slate-400">In Total Study Time</p>
        </div>
        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-1">
          <div className="text-2xl sm:text-3xl font-black text-white">Turnkey</div>
          <p className="text-xs text-slate-400">Notion &amp; Anki Templates</p>
        </div>
        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-1">
          <div className="text-2xl sm:text-3xl font-black text-emerald-400">100% Risk-Free</div>
          <p className="text-xs text-slate-400">60-Day Full Guarantee</p>
        </div>
      </div>

      {/* Curriculum Breakdown */}
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <span className="text-[10px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-2 py-0.5 rounded">
            Curriculum Specifications
          </span>
          <h2 className="text-3xl font-bold text-white">What You Will Master</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {modules.map((m, idx) => (
            <div
              key={idx}
              className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-3"
            >
              <div className="w-8 h-8 rounded-lg bg-[#d4af37]/10 text-[#d4af37] flex items-center justify-center font-bold text-xs">
                0{idx + 1}
              </div>
              <h3 className="text-base font-bold text-white">{m.title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{m.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom CTA Banner */}
      <div className="bg-gradient-to-r from-[#131b2e] to-[#1c2742] border-2 border-[#d4af37]/40 rounded-3xl p-8 sm:p-12 text-center space-y-6">
        <h2 className="text-3xl sm:text-4xl font-black text-white">
          Secure Your Academic Edge Today
        </h2>
        <p className="text-xs sm:text-sm text-slate-300 max-w-xl mx-auto leading-relaxed">
          Download the entire 7-part system, workbook templates, and cramming battleplans right now for just $15 USD.
        </p>
        <button
          onClick={() => setIsCheckoutOpen(true)}
          className="gold-btn py-4 px-10 rounded-xl text-sm font-bold uppercase tracking-wider"
        >
          Claim For $15 USD &rarr;
        </button>
      </div>

      {/* Universal Checkout Modal in USD Mode */}
      <CheckoutModal
        isOpen={isCheckoutOpen}
        onClose={() => setIsCheckoutOpen(false)}
        productSlug="academic-comeback-package"
        initialCurrency="USD"
      />
    </div>
  );
}
