'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  DollarSign,
  TrendingUp,
  MousePointer,
  Award,
  Users,
  Copy,
  CheckCheck,
  AlertCircle,
  Building,
  CheckCircle2,
  Clock,
  ArrowRight
} from 'lucide-react';

interface SaleItem {
  date: string;
  amount: number;
  commission_amount: number;
  status: string;
}

interface AffiliateData {
  code: string;
  name: string;
  email: string;
  bank_name: string;
  account_number: string;
  clicks: number;
  conversions: number;
  revenue: number;
  commission_earned: number;
  commission_paid: number;
  commission_owed: number;
  sales: SaleItem[];
  referral_link: string;
  affiliate_invite_link: string;
  direct_milestone_progress: number;
  direct_milestone_unlocked: boolean;
  direct_milestone_bonus: number;
}

function DashboardContent() {
  const searchParams = useSearchParams();
  const tokenParam = searchParams.get('token') || '';

  const [token, setToken] = useState(tokenParam);
  const [data, setData] = useState<AffiliateData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copiedRef, setCopiedRef] = useState(false);
  const [copiedInvite, setCopiedInvite] = useState(false);

  useEffect(() => {
    const savedToken = tokenParam || localStorage.getItem('ac_affiliate_token') || '';
    if (savedToken) {
      setToken(savedToken);
      fetchDashboard(savedToken);
    } else {
      setLoading(false);
    }
  }, [tokenParam]);

  const fetchDashboard = async (tok: string) => {
    setLoading(true);
    setError('');
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/affiliate/me?token=${encodeURIComponent(tok)}`);
      if (!res.ok) {
        throw new Error('Invalid or expired dashboard link. Please log in or check your email.');
      }
      const json = await res.json();
      setData(json);
      localStorage.setItem('ac_affiliate_token', tok);
    } catch (err: any) {
      setError(err.message || 'Failed to load affiliate metrics.');
    } finally {
      setLoading(false);
    }
  };

  const handleManualLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (token.trim()) {
      fetchDashboard(token.trim());
    }
  };

  if (loading) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-[#d4af37] border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-400">Loading your ambassador dashboard...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-md mx-auto bg-[#131b2e] border border-slate-800 rounded-3xl p-8 space-y-6 shadow-2xl text-center">
        <Award className="w-12 h-12 text-[#d4af37] mx-auto" />
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-white">Ambassador Portal Login</h2>
          <p className="text-xs text-slate-400">
            Enter your secret dashboard access token received upon registration.
          </p>
        </div>

        {error && (
          <div className="bg-rose-950/60 border border-rose-500/50 rounded-xl p-3 text-xs text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleManualLogin} className="space-y-4">
          <input
            type="text"
            required
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste your dashboard token here..."
            className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
          />
          <button
            type="submit"
            className="w-full gold-btn py-3.5 px-6 rounded-xl text-xs font-bold uppercase tracking-wider"
          >
            Access Dashboard &rarr;
          </button>
        </form>

        <p className="text-[11px] text-slate-500">
          Don&apos;t have an ambassador account yet?{' '}
          <Link href="/affiliate" className="text-[#d4af37] underline">
            Register here
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      {/* Top Welcome Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <span className="text-[10px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-2.5 py-1 rounded inline-block">
            Ambassador ID: {data.code}
          </span>
          <h1 className="text-2xl sm:text-4xl font-black text-white pt-2">
            Welcome back, {data.name}
          </h1>
          <p className="text-xs text-slate-400">
            Earnings split: 60% per package • Payouts bi-weekly
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              localStorage.removeItem('ac_affiliate_token');
              setData(null);
            }}
            className="text-xs text-slate-400 hover:text-white border border-slate-700 rounded-xl px-4 py-2 transition"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Total Earned</span>
            <DollarSign className="w-4 h-4 text-[#d4af37]" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-[#d4af37]">
            ₦{data.commission_earned.toLocaleString()}
          </div>
          <p className="text-[11px] text-slate-500">Lifetime referrals</p>
        </div>

        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Pending Payout</span>
            <Clock className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-emerald-400">
            ₦{data.commission_owed.toLocaleString()}
          </div>
          <p className="text-[11px] text-slate-500">Next Friday payout batch</p>
        </div>

        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Successful Sales</span>
            <Award className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-white">
            {data.conversions}
          </div>
          <p className="text-[11px] text-slate-500">Packages delivered</p>
        </div>

        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Total Link Clicks</span>
            <MousePointer className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-white">
            {data.clicks}
          </div>
          <p className="text-[11px] text-slate-500">Campus traffic</p>
        </div>
      </div>

      {/* 10-Sale Milestone Bonus Progress */}
      <div className="bg-gradient-to-r from-[#131b2e] to-[#1c2742] border border-[#d4af37]/40 rounded-3xl p-6 sm:p-8 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-widest text-[#d4af37] bg-[#d4af37]/10 px-2 py-0.5 rounded">
              🎯 Active Incentive Challenge
            </span>
            <h3 className="text-lg sm:text-xl font-bold text-white pt-1">
              Reach 10 Sales ➔ Unlock ₦10,000 Cash Bonus
            </h3>
          </div>
          <span className="text-sm font-bold text-[#d4af37]">
            {data.conversions} / 10 Completed ({data.direct_milestone_progress}%)
          </span>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
          <div
            className="bg-gradient-to-r from-[#d4af37] to-amber-200 h-full rounded-full transition-all duration-500"
            style={{ width: `${Math.min(100, data.direct_milestone_progress)}%` }}
          />
        </div>

        <p className="text-xs text-slate-300">
          {data.direct_milestone_unlocked
            ? '🎉 Congratulations! You have unlocked the ₦10,000 bonus. It will be added to your next payout.'
            : `Refer ${Math.max(0, 10 - data.conversions)} more students to unlock your ₦10,000 direct cash bonus.`}
        </p>
      </div>

      {/* Links & Bank Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Your Referral Link */}
        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-4">
          <h4 className="text-sm font-bold text-white flex items-center gap-2">
            <Award className="w-4 h-4 text-[#d4af37]" /> Your Direct Sales Link
          </h4>
          <p className="text-xs text-slate-400">
            Share this link in study groups, WhatsApp class pages, or Instagram bio.
          </p>
          <div className="bg-[#0b0f19] border border-slate-700 rounded-xl p-3 flex items-center justify-between gap-2">
            <span className="font-mono text-xs text-[#d4af37] truncate">
              {data.referral_link || `https://academiccomeback.com/r/${data.code}`}
            </span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(data.referral_link || `https://academiccomeback.com/r/${data.code}`);
                setCopiedRef(true);
                setTimeout(() => setCopiedRef(false), 2000);
              }}
              className="p-1.5 text-slate-400 hover:text-white"
            >
              {copiedRef ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Bank Account Details */}
        <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-4">
          <h4 className="text-sm font-bold text-white flex items-center gap-2">
            <Building className="w-4 h-4 text-emerald-400" /> Payout Destination
          </h4>
          <p className="text-xs text-slate-400">
            Automated direct deposit via Flutterwave Transfers.
          </p>
          <div className="bg-[#0b0f19] border border-slate-700 rounded-xl p-3 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-white">
                {data.bank_name || 'Bank Account'}
              </div>
              <div className="text-xs font-mono text-slate-400">
                {data.account_number || '••••••••••'}
              </div>
            </div>
            <span className="text-[10px] font-bold uppercase text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
              Verified
            </span>
          </div>
        </div>
      </div>

      {/* Recent Referrals Table */}
      <div className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 space-y-4">
        <h4 className="text-sm font-bold text-white">Recent Referral Sales</h4>
        {data.sales && data.sales.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Order Value</th>
                  <th className="py-3 px-4">Your Cut (60%)</th>
                  <th className="py-3 px-4">Payout Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {data.sales.map((sale, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/20">
                    <td className="py-3 px-4 text-slate-300">
                      {sale.date ? new Date(sale.date).toLocaleDateString() : 'Recent'}
                    </td>
                    <td className="py-3 px-4 font-semibold text-white">
                      ₦{sale.amount?.toLocaleString() || '5,000'}
                    </td>
                    <td className="py-3 px-4 font-bold text-[#d4af37]">
                      ₦{sale.commission_amount?.toLocaleString() || '3,000'}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                          sale.status === 'paid'
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : 'bg-amber-500/10 text-amber-300'
                        }`}
                      >
                        {sale.status || 'Pending'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-slate-400 py-6 text-center">
            No referral sales yet. Share your link with classmates and campus study groups to earn your first ₦3,000 commission!
          </p>
        )}
      </div>
    </div>
  );
}

export default function AffiliateDashboardPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Suspense fallback={<div className="text-center text-xs text-slate-400">Loading dashboard...</div>}>
        <DashboardContent />
      </Suspense>
    </div>
  );
}
