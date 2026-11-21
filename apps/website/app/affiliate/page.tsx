'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { DollarSign, Users, Award, TrendingUp, Check, ArrowRight, ShieldCheck, Copy, CheckCheck } from 'lucide-react';

export default function AffiliatePage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'register' | 'calculator'>('overview');
  const [estimatedSales, setEstimatedSales] = useState(10);
  const [copiedLink, setCopiedLink] = useState(false);

  // Registration Form State
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [bankName, setBankName] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successCode, setSuccessCode] = useState('');
  const [regError, setRegError] = useState('');

  // 60% of ₦5,000 = ₦3,000 per sale
  const commissionPerSale = 3000;
  const projectedEarnings = estimatedSales * commissionPerSale;

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setRegError('');

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/affiliate/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: fullName,
          email,
          phone,
          bank_name: bankName,
          bank_account_number: accountNumber,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Registration failed. Please check your details.');
      }

      setSuccessCode(data.referral_code || 'AC-AMBASSADOR');
    } catch (err: any) {
      setRegError(err.message || 'Error completing registration.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">
      {/* Hero Header */}
      <header className="text-center space-y-4 max-w-3xl mx-auto">
        <span className="text-[11px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-3 py-1 rounded-full inline-flex items-center gap-1.5">
          <DollarSign className="w-3.5 h-3.5" /> Campus Ambassador Program
        </span>
        <h1 className="text-3xl sm:text-5xl font-black text-white">
          Earn <span className="text-[#d4af37]">60% Instant Commission</span> on Every Recommendation
        </h1>
        <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
          Partner with Nigeria&apos;s leading academic turnaround publishing system. Get paid biweekly directly to your Nigerian bank account with full transparent tracking.
        </p>

        {/* Navigation Tabs */}
        <div className="inline-flex items-center bg-[#131b2e] border border-slate-800 rounded-xl p-1 gap-1 pt-2">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
              activeTab === 'overview'
                ? 'bg-[#d4af37] text-black shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Program Benefits
          </button>
          <button
            onClick={() => setActiveTab('calculator')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
              activeTab === 'calculator'
                ? 'bg-[#d4af37] text-black shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Earnings Calculator
          </button>
          <button
            onClick={() => setActiveTab('register')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${
              activeTab === 'register'
                ? 'bg-[#d4af37] text-black shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Apply to Join
          </button>
        </div>
      </header>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#d4af37]/10 text-[#d4af37] flex items-center justify-center font-bold">
                60%
              </div>
              <h3 className="text-lg font-bold text-white">Market-Leading Split</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                You receive ₦3,000 from every ₦5,000 purchase made with your code. The highest paying publishing partner program in Nigerian higher education.
              </p>
            </div>

            <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-bold">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-white">Biweekly Direct Bank Payouts</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Automated payments sent every alternate Friday via Flutterwave Transfers directly to your GTBank, Access, Zenith, Kuda, or OPay account.
              </p>
            </div>

            <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center font-bold">
                <Users className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-white">Sub-Affiliate Overrides</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Invite friends and fellow course reps to become ambassadors and earn an extra 10% override on all sales generated by your network.
              </p>
            </div>
          </div>

          <div className="bg-gradient-to-r from-[#131b2e] to-[#1c2742] border border-[#d4af37]/30 rounded-3xl p-8 sm:p-10 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="space-y-2 text-center md:text-left">
              <h3 className="text-2xl font-bold text-white">Ready to start earning this semester?</h3>
              <p className="text-xs sm:text-sm text-slate-300">
                It takes 60 seconds to register and get your custom tracking link and promotional assets.
              </p>
            </div>
            <button
              onClick={() => setActiveTab('register')}
              className="gold-btn py-3.5 px-8 rounded-xl text-xs font-bold uppercase tracking-wider whitespace-nowrap"
            >
              Get Your Affiliate Link &rarr;
            </button>
          </div>
        </div>
      )}

      {/* Tab 2: Earnings Calculator */}
      {activeTab === 'calculator' && (
        <div className="max-w-2xl mx-auto bg-[#131b2e] border border-slate-800 rounded-3xl p-8 sm:p-10 space-y-8 shadow-2xl">
          <div className="text-center space-y-2">
            <h3 className="text-xl font-bold text-white">Calculate Your Projected Income</h3>
            <p className="text-xs text-slate-400">
              Drag the slider to see how much you earn based on students in your class or faculty who order.
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-300">Referred Students per Month:</span>
              <span className="text-xl font-black text-[#d4af37]">{estimatedSales} students</span>
            </div>
            <input
              type="range"
              min={1}
              max={100}
              value={estimatedSales}
              onChange={(e) => setEstimatedSales(Number(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-[#d4af37]"
            />
            <div className="flex justify-between text-[11px] text-slate-500">
              <span>1 student</span>
              <span>50 students</span>
              <span>100 students</span>
            </div>
          </div>

          <div className="bg-[#0b0f19] border border-slate-800 rounded-2xl p-6 text-center space-y-2">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
              Your Estimated Commission
            </span>
            <div className="text-4xl sm:text-5xl font-black text-[#d4af37]">
              ₦{projectedEarnings.toLocaleString()}
            </div>
            <p className="text-xs text-slate-400">
              (That&apos;s ₦{commissionPerSale.toLocaleString()} &times; {estimatedSales} sales)
            </p>
          </div>

          <button
            onClick={() => setActiveTab('register')}
            className="w-full gold-btn py-3.5 px-6 rounded-xl text-xs font-bold uppercase tracking-wider"
          >
            Start Earning Now &rarr;
          </button>
        </div>
      )}

      {/* Tab 3: Register Form */}
      {activeTab === 'register' && (
        <div className="max-w-xl mx-auto">
          {successCode ? (
            <div className="bg-[#131b2e] border-2 border-emerald-500/40 rounded-3xl p-8 text-center space-y-6">
              <Award className="w-16 h-16 text-emerald-400 mx-auto" />
              <h3 className="text-2xl font-bold text-white">Ambassador Account Created!</h3>
              <p className="text-xs sm:text-sm text-slate-300">
                Your referral code is ready. Share your link with fellow students or post in study group chats to earn 60% per order.
              </p>
              <div className="bg-[#0b0f19] border border-slate-700 rounded-xl p-4 flex items-center justify-between">
                <span className="font-mono text-sm text-[#d4af37] font-bold">
                  https://academiccomeback.com/?ref={successCode}
                </span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(`https://academiccomeback.com/?ref=${successCode}`);
                    setCopiedLink(true);
                    setTimeout(() => setCopiedLink(false), 2000);
                  }}
                  className="p-2 text-slate-400 hover:text-white"
                >
                  {copiedLink ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleRegister} className="bg-[#131b2e] border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-5 shadow-2xl">
              <h3 className="text-xl font-bold text-white text-center pb-2">
                Ambassador Registration
              </h3>

              {regError && (
                <div className="bg-rose-950/60 border border-rose-500/50 rounded-xl p-3 text-xs text-rose-300">
                  {regError}
                </div>
              )}

              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Full Legal Name</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. David Itoya"
                  className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Email Address</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@email.com"
                    className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">WhatsApp / Phone</label>
                  <input
                    type="tel"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="08012345678"
                    className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Bank Name</label>
                  <input
                    type="text"
                    required
                    value={bankName}
                    onChange={(e) => setBankName(e.target.value)}
                    placeholder="e.g. GTBank, Kuda, OPay"
                    className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Account Number</label>
                  <input
                    type="text"
                    required
                    maxLength={10}
                    value={accountNumber}
                    onChange={(e) => setAccountNumber(e.target.value)}
                    placeholder="10-digit NUBAN"
                    className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full gold-btn py-3.5 px-6 rounded-xl text-xs font-bold uppercase tracking-wider mt-4"
              >
                {isSubmitting ? 'Registering...' : 'Submit Ambassador Application &rarr;'}
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
