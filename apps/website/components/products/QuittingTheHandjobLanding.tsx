'use client';

import React, { useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  ShieldCheck,
  HelpCircle,
  Activity,
  Flame,
  Trophy,
  ChevronDown,
  UserCheck
} from 'lucide-react';

interface QuittingTheHandjobLandingProps {
  onOpenCheckout: () => void;
}

const PILLARS = [
  {
    number: '01',
    tag: 'PILLAR 01 · NEUROBIOLOGY',
    title: 'Dopamine Receptor Regeneration',
    summary:
      'Understand the exact 30-day biological timeline required for your brain to regenerate downregulated D2 dopamine receptors, lifting chronic brain fog and restoring daily drive.',
    color: '#f59e0b',
    icon: Activity,
    deliverables: [
      { label: 'Delta-FosB Reversal', desc: 'Stop the hyper-stimulation cycle locking your reward pathways in perpetual craving.' },
      { label: 'The 30-Day Timeline', desc: 'Navigate the flatline phase with clear biological milestones instead of anxiety.' },
      { label: 'Prefrontal Re-Command', desc: 'Restore executive rational control over primitive subconscious impulses.' },
    ],
    kpi: 'Key Outcome: D2 Receptor Resensitization',
  },
  {
    number: '02',
    tag: 'PILLAR 02 · EXECUTION',
    title: 'The C.A.R.E. Framework',
    summary:
      'Cue Disruption, Anxiety & Urge Surfing, Radical Environmental Friction, and Energetic State Shifting. Remove willpower from the equation entirely.',
    color: '#0284c7',
    icon: ShieldCheck,
    deliverables: [
      { label: 'Cue Disruption', desc: 'Neutralize environmental and emotional triggers before cravings have power to ignite.' },
      { label: 'Radical Friction', desc: 'Install insurmountable barriers between your trigger moments and relapse devices.' },
      { label: 'Urge Surfing', desc: 'Ride dopaminergic wave peaks to natural extinction without panic or white-knuckling.' },
    ],
    kpi: 'Key Outcome: Willpower-Free System Architecture',
  },
  {
    number: '03',
    tag: 'PILLAR 03 · CRISIS PROTOCOL',
    title: 'The 5-Minute Emergency Intervention',
    summary:
      'The step-by-step physiological kill switch to deploy the exact instant an urge peaks. Shuts off the dopaminergic loop before your rational prefrontal cortex is overpowered.',
    color: '#dc2626',
    icon: Flame,
    deliverables: [
      { label: 'Parasympathetic Reset', desc: 'Deploy breathing sequences that immediately downshift acute sympathetic arousal.' },
      { label: 'Temperature Shock', desc: 'Thermal reflex protocols that snap the mind out of compulsive dopamine trance.' },
      { label: 'State Displacement', desc: 'Reroute blood flow away from the limbic system and back to executive function.' },
    ],
    kpi: 'Key Outcome: 5-Min Kill Switch Deployment',
  },
  {
    number: '04',
    tag: 'PILLAR 04 · IDENTITY',
    title: 'Identity Deconstruction & Sublimation',
    summary:
      'Stop identifying as "a recovering addict fighting temptations." Shift into complete indifference, channel raw sexual energy into high-performance physical strength and business mastery.',
    color: '#16a34a',
    icon: Trophy,
    deliverables: [
      { label: 'Identity Reset', desc: 'Eliminate streak-counting mentality and anchor your baseline in unshakeable self-command.' },
      { label: 'Sexual Transmutation', desc: 'Channel biological drive into heavy physical training, work output, and clear focus.' },
      { label: 'Sovereign Presence', desc: 'Develop grounded masculine presence, deep voice cadence, and confident authority.' },
    ],
    kpi: 'Key Outcome: Sovereign Self-Mastery',
  },
];

const CHAPTERS = [
  { num: '01', title: 'The Dopamine Trap', desc: 'How modern pornography hacks evolutionary biological circuits, downregulates androgen receptors, and why conventional self-help advice keeps men trapped.' },
  { num: '02', title: 'The Neurobiology of Relapse', desc: 'The delta-FosB accumulation cycle: why relying on willpower fails under stress, and how to outsmart subconscious cue recognition.' },
  { num: '03', title: 'The C.A.R.E. Protocol', desc: 'Engineering your physical and digital environments to place insurmountable biological barriers between you and your trigger screens.' },
  { num: '04', title: 'The 5-Minute Emergency Protocol', desc: 'The precise physical protocol to execute when an urge hits. Uses temperature shock, respiratory pacing, and parasympathetic activation.' },
  { num: '05', title: 'Dopamine Fasting & Receptor Regeneration', desc: 'What really happens in Days 1–7, 8–14, 15–30, and beyond. How to endure the flatline phase without panicking.' },
  { num: '06', title: 'Sexual Energy Sublimation', desc: 'The ancient science of transmutation: directing aggressive biological drive into heavy lifting, business execution, and study stamina.' },
  { num: '07', title: 'Conquering Emotional Triggers', desc: 'Dissecting the true roots of relapse: isolation, boredom, fatigue, and performance anxiety before they manifest physically.' },
  { num: '08', title: 'Sovereign Self-Mastery', desc: 'Building an unshakeable masculine frame, transforming vocal tone, eye contact, self-respect, and presence in every room.' },
];

export default function QuittingTheHandjobLanding({ onOpenCheckout }: QuittingTheHandjobLandingProps) {
  const [currentPillar, setCurrentPillar] = useState(0);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const pillar = PILLARS[currentPillar];
  const PillarIcon = pillar.icon;

  const faqs = [
    {
      q: 'Is my payment safe?',
      a: '100% safe. Processed through Paystack & Flutterwave with 256-bit SSL encryption. You can pay via Bank Transfer with a dedicated virtual account, or with a Mastercard/Visa card.'
    },
    {
      q: 'How does this differ from free advice on Reddit or NoFap?',
      a: 'Free online forums focus almost exclusively on "streak counters" and moral willpower. Research shows that counting days keeps your subconscious identity locked in the frame of an addict. This manual focuses on the neurochemical mechanics of dopamine receptor resensitization, the C.A.R.E. environmental framework, and our proprietary 5-minute emergency intervention.'
    },
    {
      q: 'How quickly will I receive my copy after paying?',
      a: 'Instantly. Once confirmed (typically under 10 seconds), you are redirected to your private student library to download the high-resolution PDF. A permanent backup access link is also sent to your email.'
    },
    {
      q: 'Why is it priced at only ₦5,000?',
      a: 'The normal retail value of this book is ₦20,000. We intentionally priced this launch copy at ₦5,000 so that every young man, university student, and professional who needs this freedom can afford it today without financial hardship.'
    },
    {
      q: 'What if I buy it and it doesn’t work for me?',
      a: 'Your order is protected by our 100% Risk-Free Guarantee. Apply the frameworks for 30 days. If you do not feel noticeably more in control, clear-headed, and energized, simply email support for a full 100% refund.'
    }
  ];

  return (
    <div className="space-y-20 pt-4">
      {/* Editorial Hero Quote */}
      <div className="bg-[#131b2e] border-l-4 border-[#d4af37] rounded-2xl p-6 sm:p-8 space-y-3 shadow-xl">
        <p className="text-base sm:text-xl font-bold text-white italic leading-relaxed">
          &ldquo;You are not failing because you lack discipline. You are failing because you are using moral willpower against an ancient neurobiological survival reflex.&rdquo;
        </p>
        <p className="text-xs sm:text-sm text-slate-400">
          — David Itoya, Author of <em>Quitting The Handjob</em> &amp; Founder of Scale Group
        </p>
      </div>

      {/* 4 Pillars Interactive Reframe Slider */}
      <section className="bg-[#131b2e] border border-slate-800 rounded-3xl p-6 sm:p-10 space-y-8 shadow-2xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <span className="text-[10px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-2.5 py-1 rounded inline-block">
              Core Recovery Architecture
            </span>
            <h2 className="text-2xl sm:text-3xl font-black text-white pt-2">
              The 4 Core Pillars of Neurochemical Recovery
            </h2>
          </div>

          {/* Slider Controls */}
          <div className="flex items-center gap-3 self-end sm:self-auto">
            <span className="font-mono text-xs font-bold text-[#d4af37]">
              0{currentPillar + 1} / 04
            </span>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setCurrentPillar((prev) => (prev === 0 ? PILLARS.length - 1 : prev - 1))}
                className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-[#d4af37] text-white hover:text-black flex items-center justify-center transition"
                aria-label="Previous Pillar"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                type="button"
                onClick={() => setCurrentPillar((prev) => (prev === PILLARS.length - 1 ? 0 : prev + 1))}
                className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-[#d4af37] text-white hover:text-black flex items-center justify-center transition"
                aria-label="Next Pillar"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Active Pillar Card */}
        <div
          className="bg-[#0b0f19] border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-6"
          style={{ borderLeft: `4px solid ${pillar.color}` }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center font-bold"
                style={{ backgroundColor: `${pillar.color}20`, color: pillar.color }}
              >
                <PillarIcon className="w-5 h-5" />
              </div>
              <span
                className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded"
                style={{ backgroundColor: `${pillar.color}20`, color: pillar.color }}
              >
                {pillar.tag}
              </span>
            </div>
            <span className="text-xs text-slate-500 font-mono">PROTOCOL 0{currentPillar + 1}</span>
          </div>

          <div className="space-y-3">
            <h3 className="text-xl sm:text-2xl font-bold text-white">{pillar.title}</h3>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">{pillar.summary}</p>
          </div>

          {/* Deliverables Checklist */}
          <div className="space-y-3 pt-2">
            {pillar.deliverables.map((item, idx) => (
              <div key={idx} className="bg-[#131b2e] border border-slate-800/80 rounded-xl p-3.5 flex items-start gap-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div className="text-xs text-slate-300 leading-relaxed">
                  <strong className="text-white">{item.label}:</strong> {item.desc}
                </div>
              </div>
            ))}
          </div>

          <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs">
            <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> {pillar.kpi}
            </span>
            <button
              onClick={onOpenCheckout}
              className="text-[#d4af37] hover:underline font-bold inline-flex items-center gap-1"
            >
              Get Full Protocol &rarr;
            </button>
          </div>
        </div>

        {/* Pillar Indicator Dots */}
        <div className="flex items-center justify-center gap-2 pt-2">
          {PILLARS.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentPillar(idx)}
              className={`h-2 rounded-full transition-all ${
                currentPillar === idx ? 'w-8 bg-[#d4af37]' : 'w-2 bg-slate-700'
              }`}
              aria-label={`Jump to Pillar ${idx + 1}`}
            />
          ))}
        </div>
      </section>

      {/* Chapters Grid */}
      <section className="space-y-8">
        <div className="text-center space-y-2 max-w-2xl mx-auto">
          <span className="text-[10px] uppercase font-bold tracking-widest text-[#d4af37] bg-[#d4af37]/10 px-2.5 py-1 rounded-full">
            Field Manual Structure
          </span>
          <h2 className="text-2xl sm:text-3xl font-black text-white">
            What You Will Master Inside This Book
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            8 tactical, direct, zero-fluff chapters engineered to take you from compulsive relapse to total sovereign self-command.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
          {CHAPTERS.map((ch, idx) => (
            <div
              key={idx}
              className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-3"
            >
              <span className="text-[10px] font-mono font-bold text-[#d4af37] bg-[#d4af37]/10 px-2.5 py-0.5 rounded inline-block">
                Chapter {ch.num}
              </span>
              <h3 className="text-base sm:text-lg font-bold text-white">{ch.title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{ch.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Author Bio Section */}
      <section className="bg-[#131b2e] border border-slate-800 rounded-3xl p-6 sm:p-10 grid grid-cols-1 md:grid-cols-12 gap-8 items-center">
        <div className="md:col-span-4 text-center md:text-left space-y-3">
          <div className="w-28 h-28 rounded-2xl bg-gradient-to-tr from-[#d4af37] to-amber-200 p-1 mx-auto md:mx-0 shadow-xl">
            <div className="w-full h-full bg-[#0b0f19] rounded-xl flex items-center justify-center font-black text-3xl text-[#d4af37]">
              DI
            </div>
          </div>
          <h3 className="text-xl font-bold text-white">David Itoya</h3>
          <p className="text-xs text-[#d4af37] font-semibold">Author &amp; Founder, Scale Group</p>
        </div>

        <div className="md:col-span-8 space-y-4 text-xs sm:text-sm text-slate-300 leading-relaxed">
          <p>
            I spent years watching exceptionally talented, ambitious young men slowly destroy their drive, edge, and self-esteem through private, compulsive habits they couldn&apos;t talk about to anyone. They were told they were &ldquo;weak&rdquo; or &ldquo;sinful,&rdquo; but nobody gave them the clinical, neuroscience-grounded tools to fix the feedback loop.
          </p>
          <p>
            I wrote <em>Quitting The Handjob</em> to eliminate the stigma and replace helpless willpower with an uncompromising biological battle plan. If you are ready to reclaim your mind, your masculine power, and your clean conscience, this manual was written for you.
          </p>
          <div className="pt-2 flex flex-wrap gap-4 text-xs font-semibold text-slate-400">
            <span className="flex items-center gap-1.5"><ShieldCheck className="w-4 h-4 text-emerald-400" /> High-Performance Mentor</span>
            <span className="flex items-center gap-1.5"><UserCheck className="w-4 h-4 text-sky-400" /> Thousands of Young Men Guided Across Scale Group</span>
          </div>
        </div>
      </section>

      {/* Two Choices Crossroads Section */}
      <section className="space-y-6">
        <div className="text-center space-y-2 max-w-xl mx-auto">
          <h3 className="text-2xl sm:text-3xl font-black text-white">
            You Stand at a Crossroads Right Now
          </h3>
          <p className="text-xs sm:text-sm text-slate-400">
            Continuing on the current path has a real, tangible cost to your future self.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
          {/* Path 1: Bad */}
          <div className="bg-rose-950/20 border-2 border-rose-500/40 rounded-3xl p-6 sm:p-8 space-y-4">
            <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400 bg-rose-500/10 px-2.5 py-1 rounded">
              Path 1: The Cost of Inaction
            </span>
            <h4 className="text-xl font-bold text-white">Stay in the Hidden Loop</h4>
            <div className="text-xs sm:text-sm text-slate-300 space-y-3 leading-relaxed">
              <p>
                You close this page. You tell yourself you&apos;ll &ldquo;do better this time.&rdquo; Three days from now, late at night when stress or boredom creeps in, you cave again.
              </p>
              <p>
                You wake up tomorrow with the same familiar brain fog, reduced motivation, low eye contact, and the quiet, agonizing sense that you are failing yourself in private.
              </p>
            </div>
          </div>

          {/* Path 2: Good */}
          <div className="bg-[#131b2e] border-2 border-[#d4af37] rounded-3xl p-6 sm:p-8 space-y-4 shadow-2xl">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#d4af37] bg-[#d4af37]/10 px-2.5 py-1 rounded">
              Path 2: Sovereign Mastery
            </span>
            <h4 className="text-xl font-bold text-white">Install a Clinical Recovery System</h4>
            <div className="text-xs sm:text-sm text-slate-300 space-y-3 leading-relaxed">
              <p>
                You invest ₦5,000 today (less than the price of a single lunch). Within 30 minutes, you understand the exact neurochemical triggers that were pulling your strings.
              </p>
              <p>
                You install the C.A.R.E. protocol, neutralize urges on demand with the 5-Minute Emergency Protocol, heal your dopamine receptors, and walk with the quiet, masculine presence of a man who commands his own mind.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQs */}
      <section className="bg-[#131b2e] border border-slate-800 rounded-3xl p-6 sm:p-10 space-y-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-[#d4af37]" /> Frequently Asked Questions
        </h3>
        <div className="space-y-3">
          {faqs.map((faq, idx) => (
            <div
              key={idx}
              className="bg-[#0b0f19] border border-slate-800 rounded-xl overflow-hidden transition"
            >
              <button
                type="button"
                onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                className="w-full text-left p-4 sm:p-5 flex items-center justify-between gap-4 font-semibold text-xs sm:text-sm text-white hover:text-[#d4af37]"
              >
                <span>{faq.q}</span>
                <ChevronDown
                  className={`w-4 h-4 shrink-0 transition-transform ${
                    openFaq === idx ? 'rotate-180 text-[#d4af37]' : 'text-slate-500'
                  }`}
                />
              </button>
              {openFaq === idx && (
                <div className="px-4 pb-4 sm:px-5 sm:pb-5 text-xs text-slate-300 leading-relaxed border-t border-slate-800/80 pt-3">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
