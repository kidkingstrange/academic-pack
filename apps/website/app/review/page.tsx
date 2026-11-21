'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Star, CheckCircle, AlertCircle, Send, Award, ArrowLeft } from 'lucide-react';

function ReviewFormContent() {
  const searchParams = useSearchParams();
  const tokenFromUrl = searchParams.get('token') || '';

  const [token, setToken] = useState(tokenFromUrl);
  const [rating, setRating] = useState(5);
  const [hoverRating, setHoverRating] = useState(0);
  const [displayName, setDisplayName] = useState('');
  const [reviewText, setReviewText] = useState('');
  const [institution, setInstitution] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (tokenFromUrl) {
      setToken(tokenFromUrl);
    }
  }, [tokenFromUrl]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setErrorMessage('Please provide your verified purchase token from your order confirmation email.');
      return;
    }
    if (reviewText.trim().length < 20) {
      setErrorMessage('Please share at least a short 2-3 sentence review of your experience.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage('');

    try {
      const formData = new FormData();
      formData.append('token', token);
      formData.append('rating', rating.toString());
      formData.append('text', `${reviewText}${institution ? ` — ${institution}` : ''}`);
      if (displayName) formData.append('display_name', displayName);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/reviews`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to submit review. Token may be invalid or expired.');
      }

      setSubmitted(true);
    } catch (err: any) {
      setErrorMessage(err.message || 'Error submitting review. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="bg-[#131b2e] border-2 border-emerald-500/40 rounded-3xl p-8 sm:p-12 text-center max-w-xl mx-auto space-y-6">
        <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto" />
        <h2 className="text-2xl sm:text-3xl font-black text-white">Review Received! 🎉</h2>
        <p className="text-sm text-slate-300 leading-relaxed">
          Thank you for sharing your experience! Your review has been submitted for verification. As promised, a <strong>20% discount gift code</strong> has been dispatched to your email for your next purchase.
        </p>
        <div className="pt-4">
          <Link href="/" className="gold-btn py-3 px-6 rounded-xl text-xs font-bold uppercase">
            Return to Homepage &rarr;
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center space-y-3">
        <span className="text-[11px] font-bold text-[#d4af37] uppercase tracking-widest bg-[#d4af37]/10 px-3 py-1 rounded-full inline-flex items-center gap-1.5">
          <Award className="w-3.5 h-3.5" /> Verified Customer Social Proof
        </span>
        <h1 className="text-3xl sm:text-4xl font-black text-white">
          Share Your Academic Experience
        </h1>
        <p className="text-xs sm:text-sm text-slate-300 max-w-md mx-auto">
          Help other students choose the right study system. Verified reviewers instantly receive a 20% discount code.
        </p>
      </div>

      {errorMessage && (
        <div className="bg-rose-950/60 border border-rose-500/50 rounded-xl p-4 flex items-center gap-3 text-xs text-rose-300">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Review Form */}
      <form onSubmit={handleSubmit} className="bg-[#131b2e] border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-2xl">
        {/* Star Rating Picker */}
        <div className="space-y-2 text-center pb-2">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
            Your Overall Rating
          </label>
          <div className="flex items-center justify-center gap-2">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                type="button"
                key={star}
                onMouseEnter={() => setHoverRating(star)}
                onMouseLeave={() => setHoverRating(0)}
                onClick={() => setRating(star)}
                className="p-1 transition transform hover:scale-110"
              >
                <Star
                  className={`w-8 h-8 ${
                    (hoverRating || rating) >= star
                      ? 'text-[#d4af37] fill-[#d4af37]'
                      : 'text-slate-600'
                  }`}
                />
              </button>
            ))}
          </div>
          <span className="text-xs text-slate-400">
            {rating === 5 ? 'Exceptional (5/5)' : `${rating} out of 5 stars`}
          </span>
        </div>

        {/* Token Input (if not in URL) */}
        {!tokenFromUrl && (
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">
              Verified Order Token <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="e.g. rev_tok_9f8a2..."
              className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
            />
            <p className="text-[11px] text-slate-500">
              Found in your delivery email receipt.
            </p>
          </div>
        )}

        {/* Display Name */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-300">
            Display Name / Initials
          </label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. Emmanuel O. or anonymous"
            className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
          />
        </div>

        {/* Institution / Department */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-300">
            Institution & Department (Optional)
          </label>
          <input
            type="text"
            value={institution}
            onChange={(e) => setInstitution(e.target.value)}
            placeholder="e.g. UNILAG Mechanical Eng / 300L"
            className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl px-4 py-3 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37]"
          />
        </div>

        {/* Review Text */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-300">
            Your Honest Feedback <span className="text-rose-400">*</span>
          </label>
          <textarea
            required
            rows={5}
            value={reviewText}
            onChange={(e) => setReviewText(e.target.value)}
            placeholder="How did the system help your study routine, exam preparation, or CGPA? What was the biggest breakthrough for you?"
            className="w-full bg-[#0b0f19] border border-slate-700 rounded-xl p-4 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-[#d4af37] leading-relaxed"
          />
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full gold-btn py-3.5 px-6 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2"
        >
          {isSubmitting ? (
            <span>Verifying & Submitting...</span>
          ) : (
            <>
              <Send className="w-4 h-4" /> Submit Verified Review
            </>
          )}
        </button>
      </form>
    </div>
  );
}

export default function ReviewPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Suspense fallback={<div className="text-center text-xs text-slate-400">Loading review interface...</div>}>
        <ReviewFormContent />
      </Suspense>
    </div>
  );
}
