'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { LibraryBook } from '@repo/api-contracts';
import { BookOpen, Download, Lock, CheckCircle2, Search, AlertCircle } from 'lucide-react';

function LibraryContent() {
  const searchParams = useSearchParams();
  const initialToken = searchParams.get('token') || '';

  const [token, setToken] = useState(initialToken);
  const [books, setBooks] = useState<LibraryBook[]>([]);
  const [userEmail, setUserEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLibrary = async (accessToken: string) => {
    if (!accessToken.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'https://edgepack.thescaleconference.com';
      const res = await fetch(`${apiBase}/api/library/books?token=${encodeURIComponent(accessToken.trim())}`);
      if (!res.ok) {
        throw new Error('Invalid or expired library token. Please check your purchase email.');
      }
      const data = await res.json();
      setBooks(data.books || []);
      setUserEmail(data.email || '');
    } catch (err: any) {
      setError(err.message || 'Could not load your library.');
      setBooks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialToken) {
      fetchLibrary(initialToken);
    }
  }, [initialToken]);

  const handleDownload = async (slug: string) => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'https://edgepack.thescaleconference.com';
      const res = await fetch(`${apiBase}/api/library/download/${encodeURIComponent(slug)}?token=${encodeURIComponent(token.trim())}`);
      if (!res.ok) throw new Error('Could not generate download link.');
      const data = await res.json();
      if (data.download_url) {
        window.open(data.download_url, '_blank');
      }
    } catch (err: any) {
      alert('Download error: ' + err.message);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
      {/* Header */}
      <div className="text-center space-y-3 max-w-xl mx-auto">
        <span className="text-[10px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-2.5 py-1 rounded">
          Student Portal
        </span>
        <h1 className="text-3xl sm:text-4xl font-black text-white">Your Digital Reading Library</h1>
        <p className="text-xs sm:text-sm text-slate-400">
          Access all your purchased masterclass books, DRM-free study manuals, and automated email curriculum materials.
        </p>
      </div>

      {/* Access Token Input Box */}
      <div className="max-w-md mx-auto bg-[#131b2e] border border-[#d4af37]/30 rounded-2xl p-6 shadow-xl space-y-4">
        <label className="block text-xs font-semibold text-slate-300">
          Enter Your Library Access Token
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="e.g. 9f8a7b6c5d4e..."
            className="flex-1 bg-[#0b0f19] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
          />
          <button
            onClick={() => fetchLibrary(token)}
            disabled={loading || !token.trim()}
            className="gold-btn px-4 py-2 rounded-lg text-xs font-bold uppercase transition disabled:opacity-50"
          >
            {loading ? 'Verifying...' : 'Access'}
          </button>
        </div>
        <span className="text-[11px] text-slate-400 block">
          💡 Your access token was sent to your email immediately after payment verification.
        </span>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="max-w-md mx-auto bg-red-500/10 border border-red-500/30 text-red-400 text-xs p-4 rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Books Grid */}
      {books.length > 0 && (
        <div className="space-y-6">
          <div className="flex justify-between items-center border-b border-slate-800 pb-4">
            <h2 className="text-lg font-bold text-white">Your Unlocked Books ({books.length})</h2>
            {userEmail && <span className="text-xs text-slate-400">Enrolled: {userEmail}</span>}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {books.map((b) => (
              <div
                key={b.slug}
                className="bg-[#131b2e] border border-slate-800 rounded-2xl p-6 flex flex-col justify-between space-y-4 shadow-lg hover:border-[#d4af37]/40 transition"
              >
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-[#f3e5ab] bg-[#d4af37]/10 px-2 py-0.5 rounded">
                    {b.category || 'Masterclass'}
                  </span>
                  <h3 className="text-base font-bold text-white">{b.title}</h3>
                </div>

                <div className="flex gap-2 pt-4 border-t border-slate-800">
                  <button
                    onClick={() => handleDownload(b.slug)}
                    className="flex-1 gold-btn py-2.5 px-3 rounded-lg text-xs font-bold uppercase flex items-center justify-center gap-1.5"
                  >
                    <Download className="w-3.5 h-3.5" /> Download PDF
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function LibraryPage() {
  return (
    <Suspense fallback={<div className="text-center py-20 text-slate-400">Loading library...</div>}>
      <LibraryContent />
    </Suspense>
  );
}
