import { MetadataRoute } from 'next';
import fs from 'fs';
import path from 'path';
import { CANONICAL_PRODUCTS } from '@/lib/products';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://academiccomeback.com';

  // Core static pages
  const coreRoutes: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1.0,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.9,
    },
    {
      url: `${baseUrl}/library`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${baseUrl}/affiliate`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/review`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.6,
    },
  ];

  // Canonical product pages
  const productRoutes: MetadataRoute.Sitemap = CANONICAL_PRODUCTS.map((prod) => ({
    url: `${baseUrl}/products/${prod.slug}`,
    lastModified: new Date(),
    changeFrequency: 'weekly',
    priority: 0.95,
  }));

  // Category hub routes
  const categories = [
    'academics',
    'balancing-work-and-school',
    'finances',
    'hostel-and-accommodation',
    'mental-health',
  ];

  const categoryRoutes: MetadataRoute.Sitemap = categories.map((cat) => ({
    url: `${baseUrl}/blog/${cat}`,
    lastModified: new Date(),
    changeFrequency: 'weekly',
    priority: 0.85,
  }));

  // 201+ Blog post routes
  let blogRoutes: MetadataRoute.Sitemap = [];
  try {
    const manifestPath = path.join(process.cwd(), 'data', 'blog', 'manifest.json');
    if (fs.existsSync(manifestPath)) {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
      blogRoutes = manifest.map((post: { category: string; slug: string; dateModified?: string }) => ({
        url: `${baseUrl}/blog/${post.category}/${post.slug}`,
        lastModified: post.dateModified ? new Date(post.dateModified) : new Date(),
        changeFrequency: 'weekly',
        priority: 0.8,
      }));
    }
  } catch (err) {
    console.error('Error generating blog sitemap:', err);
  }

  return [...coreRoutes, ...productRoutes, ...categoryRoutes, ...blogRoutes];
}
