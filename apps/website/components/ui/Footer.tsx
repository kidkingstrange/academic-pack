import React from 'react';
import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="bg-[#070a11] border-t border-slate-800/80 text-slate-400 text-xs py-12 px-4 sm:px-6 lg:px-8 mt-24">
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
        {/* Brand Overview */}
        <div className="space-y-3">
          <span className="font-extrabold text-base tracking-wider uppercase text-[#f3e5ab]">
            SCALE <span className="text-[#d4af37]">GROUP</span>
          </span>
          <p className="text-slate-400 leading-relaxed text-xs">
            Digital publishing house and accelerated execution masterclasses designed for university students, high-performance freelancers, and ambitious operators.
          </p>
        </div>

        {/* Quick Links */}
        <div>
          <h4 className="text-white font-semibold mb-3 uppercase tracking-wider text-xs">Masterclasses</h4>
          <ul className="space-y-2">
            <li><Link href="/products/academic-comeback-package" className="hover:text-[#d4af37] transition">The Academic Comeback Package</Link></li>
            <li><Link href="/products/quitting-the-handjob" className="hover:text-[#d4af37] transition">Quitting The Handjob</Link></li>
            <li><Link href="/products/how-to-close-high-paying-clients-in-the-dms" className="hover:text-[#d4af37] transition">How to Close Clients in the DMs</Link></li>
            <li><Link href="/products/what-to-do-when-your-boss-is-angry-with-you" className="hover:text-[#d4af37] transition">When Your Boss Is Angry With You</Link></li>
          </ul>
        </div>

        {/* Student Resources */}
        <div>
          <h4 className="text-white font-semibold mb-3 uppercase tracking-wider text-xs">Student Portal</h4>
          <ul className="space-y-2">
            <li><Link href="/library" className="hover:text-[#d4af37] transition">Access Your Library</Link></li>
            <li><Link href="/affiliates/dashboard" className="hover:text-[#d4af37] transition">Affiliate Program (60%)</Link></li>
            <li><a href="https://chat.whatsapp.com/Ia7VkMigSlq2NIRQt7A3yj" target="_blank" rel="noopener noreferrer" className="hover:text-[#d4af37] transition">WhatsApp Community</a></li>
          </ul>
        </div>

        {/* Legal & Compliance (CAN-SPAM / NDPA) */}
        <div className="space-y-2">
          <h4 className="text-white font-semibold mb-3 uppercase tracking-wider text-xs">Legal &amp; Compliance</h4>
          <p className="leading-relaxed">
            Scale Group Digital Publishing • 8 The Scale Conference Blvd, Victoria Island, Lagos, Nigeria.
          </p>
          <p>
            Customer Support: <a href="mailto:support@thescaleconference.com" className="text-[#d4af37] underline">support@thescaleconference.com</a>
          </p>
          <p className="pt-2">
            © {new Date().getFullYear()} Scale Group. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
