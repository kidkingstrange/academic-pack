/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
      {
        protocol: 'http',
        hostname: 'localhost',
      },
    ],
  },
  async redirects() {
    return [
      // 301 Permanent Redirects for all legacy HTML blog posts
      {
        source: '/blog/academics/:slug.html',
        destination: '/blog/academics/:slug',
        permanent: true,
      },
      {
        source: '/blog/academics/:slug/index.html',
        destination: '/blog/academics/:slug',
        permanent: true,
      },
      // 301 Permanent Redirects for standalone book landing pages
      {
        source: '/academic-comeback-package.html',
        destination: '/products/academic-comeback-package',
        permanent: true,
      },
      {
        source: '/quitting-the-handjob.html',
        destination: '/products/quitting-the-handjob',
        permanent: true,
      },
      {
        source: '/how-to-close-high-paying-clients-in-the-dms.html',
        destination: '/products/how-to-close-high-paying-clients-in-the-dms',
        permanent: true,
      },
      {
        source: '/what-to-do-when-your-boss-is-angry-with-you.html',
        destination: '/products/what-to-do-when-your-boss-is-angry-with-you',
        permanent: true,
      },
      {
        source: '/what-to-do-after-a-breakup.html',
        destination: '/products/what-to-do-after-a-breakup',
        permanent: true,
      },
      {
        source: '/how-to-do-your-ideas.html',
        destination: '/products/how-to-do-your-ideas',
        permanent: true,
      },
      {
        source: '/library.html',
        destination: '/library',
        permanent: true,
      },
      {
        source: '/affiliate-dashboard.html',
        destination: '/affiliate/dashboard',
        permanent: true,
      },
      {
        source: '/affiliates/dashboard',
        destination: '/affiliate/dashboard',
        permanent: true,
      },
      {
        source: '/affiliate-register.html',
        destination: '/affiliate',
        permanent: true,
      },
      {
        source: '/affiliate-activate.html',
        destination: '/affiliate/activate',
        permanent: true,
      },
      {
        source: '/us.html',
        destination: '/us',
        permanent: true,
      },
      {
        source: '/usa',
        destination: '/us',
        permanent: true,
      },
      {
        source: '/united-states',
        destination: '/us',
        permanent: true,
      },
    ];
  },
};

module.exports = nextConfig;
