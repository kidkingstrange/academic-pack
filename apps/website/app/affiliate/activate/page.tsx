'use client';

import React, { useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Lock, CheckCircle, AlertCircle, ShieldCheck } from 'lucide-react';

function ActivateContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [email, setEmail] = useState(searchParams.get('email') || '');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleActivate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/affiliate/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Activation failed. Please check your email or registration status.');
      }

      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Error activating account.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="max-w-md mx-auto bg-[#131b2e] border-2 border-emerald-500/40 rounded-3xl p-8 text-center space-y-6 shadow-2xl">
        <CheckCircle className="w-14 h-14 text-emerald-400 mx-auto" />
        <h2 className="text-2xl font-bold text-white">Password Activated!</h2>
        <p className="text-xs text-slate-300">
          Your password has been securely registered. You can now access your private ambassador dashboard.
        </p>
        <Link
          href="/affiliate/dashboard"
          className="gold-btn py-3 px-6 rounded-xl text-xs font-bold uppercase inline-block"
        >
          Go To Ambassador Dashboard &rarr;
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto bg-[#131b2e] border border-slate-800 rounded-3xl p-8 space-y-6 shadow-2xl">
      <div className="text-center space-y-2">
        <ShieldCheck className="w-12 h-12 text-[#d4af37] mx-auto" />
        <h1 className="text-2xl font-bold text-white">Set Your Password</h1>
        <p className="text-xs text-slate-400">
          Create a personal password to secure your ambassador account and payouts.
        </p>
      </div>

      {error && (
        <div className="bg-rose-950/60 border border-rose-500/50 rounded-xl p-3 text-xs text-rose-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleActivate} className="space-y-4">
        <div className="space-y-1">
          <label className="text-xs font-medium text-slate-300">Registered Email</label>
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
          <label className="text-xs font-medium text-slate-300">New Password</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-slate-300">Confirm Password</label>
          <input
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full gold-btn py-3.5 px-6 rounded-xl text-xs font-bold uppercase tracking-wider mt-2"
        >
          {loading ? 'Activating...' : 'Activate Password & Login'}
        </button>
      </form>
    </div>
  );
}

export default function ActivatePage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <Suspense fallback={<div className="text-center text-xs text-slate-400">Loading activation...</div>}>
        <ActivateContent />
      </Suspense>
    </div>
  );
}
