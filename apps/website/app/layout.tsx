import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/ui/Navbar';
import Footer from '@/components/ui/Footer';

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'https://academiccomeback.com'),
  title: {
    default: 'The Academic Comeback Package | Scale Group Digital Masterclasses',
    template: '%s | Scale Group Publishing',
  },
  description: 'The proven operating system to rescue failing GPAs, master technical university coursework in 14 days, and build elite mental discipline.',
  keywords: [
    'academic comeback package',
    'study habits first class students',
    'how to study for nigerian university exams',
    'active recall study guide',
    'how to close clients in DMs',
    'quitting the handjob',
  ],
  authors: [{ name: 'David Itoya' }],
  creator: 'Scale Group Publishing',
  openGraph: {
    type: 'website',
    locale: 'en_NG',
    url: 'https://academiccomeback.com',
    title: 'The Academic Comeback Package | Scale Group Publishing',
    description: 'Transform your university grades and mental stamina. Instant PDF manuals & 52-week automated study mastery.',
    siteName: 'Scale Group Publishing',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'The Academic Comeback Package | Scale Group',
    description: 'Transform your university grades and mental stamina. Instant digital access.',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        {/* Organization Schema.org Structured Data */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'Organization',
              name: 'Scale Group Publishing',
              url: 'https://academiccomeback.com',
              logo: 'https://academiccomeback.com/assets/images/logo.png',
              sameAs: [
                'https://chat.whatsapp.com/Ia7VkMigSlq2NIRQt7A3yj',
              ],
              contactPoint: {
                '@type': 'ContactPoint',
                email: 'support@thescaleconference.com',
                contactType: 'Customer Support',
              },
            }),
          }}
        />
      </head>
      <body className="bg-[#0b0f19] text-slate-100 flex flex-col min-h-screen">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
