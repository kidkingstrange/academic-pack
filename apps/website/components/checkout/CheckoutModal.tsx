'use client';

import React, { useState } from 'react';
import { Product } from '@repo/api-contracts';
import { X, ShieldCheck, CreditCard, Lock, CheckCircle2 } from 'lucide-react';

interface CheckoutModalProps {
  product: Product;
  isOpen: boolean;
  onClose: () => void;
}

export default function CheckoutModal({ product, isOpen, onClose }: CheckoutModalProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [affiliateCode, setAffiliateCode] = useState('');
  const [currency, setCurrency] = useState<'NGN' | 'USD'>('NGN');
  const [gateway, setGateway] = useState<'paystack' | 'flutterwave'>('paystack');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const priceFormatted = currency === 'NGN'
    ? `₦${product.priceNaira.toLocaleString()}`
    : `$${product.priceUsd}`;

  const regularFormatted = currency === 'NGN'
    ? `₦${product.regularPriceNaira.toLocaleString()}`
    : `$${product.regularPriceUsd}`;

  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'https://edgepack.thescaleconference.com';
      const res = await fetch(`${apiBase}/api/payments/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim().toLowerCase(),
          product_slug: product.slug,
          affiliate_code: affiliateCode.trim() || undefined,
          currency: currency,
          gateway: gateway,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to initialize payment');
      }

      const initData = await res.json();

      // If gateway returned authorization_url, redirect customer to secure hosted payment page
      if (initData.authorization_url) {
        window.location.href = initData.authorization_url;
      } else if (initData.checkout_url) {
        window.location.href = initData.checkout_url;
      } else {
        throw new Error('Payment gateway did not provide a valid authorization URL.');
      }
    } catch (err: any) {
      setError(err.message || 'Payment initiation failed. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-[#131b2e] border border-[#d4af37]/30 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl relative">
        {/* Header */}
        <div className="p-6 bg-gradient-to-b from-[#1e293b] to-[#131b2e] border-b border-slate-700/50 flex justify-between items-start">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-widest text-[#d4af37] bg-[#d4af37]/10 px-2 py-0.5 rounded">
              Secure Instant Checkout
            </span>
            <h3 className="text-lg font-bold text-white mt-1.5 leading-snug">{product.title}</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg transition"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content & Form */}
        <form onSubmit={handleCheckout} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs p-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Pricing Banner */}
          <div className="bg-[#0b0f19] border border-slate-800 rounded-xl p-4 flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-400 block">Total Due Now:</span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-black text-[#d4af37]">{priceFormatted}</span>
                <span className="text-xs text-slate-500 line-through">{regularFormatted}</span>
              </div>
            </div>
            <div className="flex items-center gap-1 bg-emerald-500/10 text-emerald-400 text-[11px] font-semibold px-2.5 py-1 rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5" /> Instant Delivery
            </div>
          </div>

          {/* Name Field */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Your Full Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Tobi Adebayo"
              className="w-full bg-[#0b0f19] border border-slate-700 rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
            />
          </div>

          {/* Email Field */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Delivery Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@gmail.com"
              className="w-full bg-[#0b0f19] border border-slate-700 rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
            />
            <span className="text-[11px] text-slate-400 mt-1 block">Your download link and library credentials will be sent here immediately.</span>
          </div>

          {/* Currency Toggle */}
          <div className="grid grid-cols-2 gap-3 pt-1">
            <button
              type="button"
              onClick={() => setCurrency('NGN')}
              className={`py-2 text-xs font-semibold rounded-lg border transition ${
                currency === 'NGN'
                  ? 'bg-[#d4af37]/20 border-[#d4af37] text-[#f3e5ab]'
                  : 'bg-[#0b0f19] border-slate-700 text-slate-400 hover:text-white'
              }`}
            >
              🇳🇬 Naira (NGN)
            </button>
            <button
              type="button"
              onClick={() => setCurrency('USD')}
              className={`py-2 text-xs font-semibold rounded-lg border transition ${
                currency === 'USD'
                  ? 'bg-[#d4af37]/20 border-[#d4af37] text-[#f3e5ab]'
                  : 'bg-[#0b0f19] border-slate-700 text-slate-400 hover:text-white'
              }`}
            >
              🇺🇸 US Dollars (USD)
            </button>
          </div>

          {/* Gateway Selection */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setGateway('paystack')}
              className={`py-2 px-3 text-xs font-semibold rounded-lg border flex items-center justify-center gap-1.5 transition ${
                gateway === 'paystack'
                  ? 'bg-[#d4af37]/15 border-[#d4af37] text-white'
                  : 'bg-[#0b0f19] border-slate-700 text-slate-400'
              }`}
            >
              <CreditCard className="w-3.5 h-3.5" /> Paystack
            </button>
            <button
              type="button"
              onClick={() => setGateway('flutterwave')}
              className={`py-2 px-3 text-xs font-semibold rounded-lg border flex items-center justify-center gap-1.5 transition ${
                gateway === 'flutterwave'
                  ? 'bg-[#d4af37]/15 border-[#d4af37] text-white'
                  : 'bg-[#0b0f19] border-slate-700 text-slate-400'
              }`}
            >
              <CreditCard className="w-3.5 h-3.5" /> Flutterwave
            </button>
          </div>

          {/* Submit CTA */}
          <button
            type="submit"
            disabled={loading}
            className="w-full gold-btn py-3.5 rounded-xl font-bold text-sm tracking-wide uppercase flex items-center justify-center gap-2 mt-4 shadow-lg disabled:opacity-50"
          >
            {loading ? (
              <span>Initiating Secure Checkout...</span>
            ) : (
              <>
                <Lock className="w-4 h-4" /> Pay {priceFormatted} &amp; Access Library
              </>
            )}
          </button>

          {/* Trust Footnote */}
          <div className="text-center text-[11px] text-slate-400 flex items-center justify-center gap-1 pt-2">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> 256-Bit SSL Encrypted &bull; Instant PDF Access
          </div>
        </form>
      </div>
    </div>
  );
}
