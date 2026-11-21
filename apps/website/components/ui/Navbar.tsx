'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { BookOpen, Library, Award, Menu, X, ShoppingCart } from 'lucide-react';

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 bg-[#0b0f19]/90 backdrop-blur-md border-b border-[#d4af37]/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <span className="font-extrabold text-xl tracking-wider uppercase text-[#f3e5ab]">
              SCALE <span className="text-[#d4af37]">GROUP</span>
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            <Link href="/#products" className="text-sm font-medium text-slate-300 hover:text-[#d4af37] transition">
              Books &amp; Masterclasses
            </Link>
            <Link href="/products/academic-comeback-package" className="text-sm font-semibold text-[#f3e5ab] hover:text-[#d4af37] transition flex items-center gap-1.5">
              <span className="bg-[#d4af37]/20 text-[#d4af37] text-xs px-2 py-0.5 rounded-full font-bold">₦5,000 PROMO</span>
              Academic Comeback
            </Link>
            <Link href="/library" className="text-sm font-medium text-slate-300 hover:text-[#d4af37] transition flex items-center gap-1">
              <Library className="w-4 h-4" /> Student Library
            </Link>
            <Link href="/affiliates/dashboard" className="text-sm font-medium text-slate-300 hover:text-[#d4af37] transition flex items-center gap-1">
              <Award className="w-4 h-4" /> Affiliate Portal (60%)
            </Link>
            <Link
              href="/products/academic-comeback-package"
              className="gold-btn px-4 py-2 rounded-full text-xs uppercase tracking-wider flex items-center gap-1.5"
            >
              <ShoppingCart className="w-3.5 h-3.5" /> Get Package Now
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="text-slate-300 hover:text-white p-2"
              aria-label="Toggle Menu"
            >
              {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {isOpen && (
        <div className="md:hidden bg-[#131b2e] border-b border-[#d4af37]/20 px-4 pt-2 pb-6 space-y-3">
          <Link
            href="/#products"
            onClick={() => setIsOpen(false)}
            className="block text-slate-300 hover:text-[#d4af37] font-medium py-2"
          >
            Books &amp; Masterclasses
          </Link>
          <Link
            href="/products/academic-comeback-package"
            onClick={() => setIsOpen(false)}
            className="block text-[#f3e5ab] font-semibold py-2"
          >
            Academic Comeback Package (₦5,000)
          </Link>
          <Link
            href="/library"
            onClick={() => setIsOpen(false)}
            className="block text-slate-300 hover:text-[#d4af37] font-medium py-2"
          >
            Student Library
          </Link>
          <Link
            href="/affiliates/dashboard"
            onClick={() => setIsOpen(false)}
            className="block text-slate-300 hover:text-[#d4af37] font-medium py-2"
          >
            Affiliate Portal (60% Commission)
          </Link>
          <Link
            href="/products/academic-comeback-package"
            onClick={() => setIsOpen(false)}
            className="block text-center gold-btn py-3 rounded-lg text-sm uppercase mt-4"
          >
            Get Academic Comeback Now (₦5,000)
          </Link>
        </div>
      )}
    </nav>
  );
}
