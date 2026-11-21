import '../models/product_model.dart';

class ProductRepository {
  static const List<ProductModel> canonicalProducts = [
    ProductModel(
      id: 'PROD-ACP',
      slug: 'academic-comeback-package',
      title: 'The Academic Comeback Package (7-in-1 Study System)',
      description: 'The definitive complete operating system to rescue failing GPAs, master technical coursework in 14 days, and build elite academic discipline.',
      priceNaira: 5000,
      regularPriceNaira: 20000,
      priceUsd: 15.0,
      regularPriceUsd: 100.0,
      category: 'Academics & Study Skills',
      benefits: [
        'Rescue low GPAs within a single academic semester',
        'Deconstruct complex 300/400-level coursework into actionable study templates',
        'Master the 2-Hour Active Recall Exam Cramming Protocol',
      ],
      features: [
        'The 7 Core Masterclass Manuals in DRM-free Digital PDF format',
        'Weekly Active Recall Spreadsheet Study Trackers',
        '52-Week Automated Academic Mastery Email Curriculum',
      ],
      isBundle: true,
    ),
    ProductModel(
      id: 'PROD-QTH',
      slug: 'quitting-the-handjob',
      title: 'Quitting The Handjob',
      description: 'A clinical, direct neurochemical protocol to permanently eliminate compulsive pornography habits, restore dopamine baseline, and rebuild unstoppable self-respect.',
      priceNaira: 5000,
      regularPriceNaira: 25000,
      priceUsd: 15.0,
      regularPriceUsd: 40.0,
      category: 'Mindset & Self-Mastery',
      benefits: [
        'Rewire compulsive neurochemical reward loops in 21 days',
        'Restore natural dopamine sensitivity, drive, and mental sharpness',
        'Eliminate brain fog, shame cycles, and social anxiety',
      ],
      features: [
        '21-Day Step-by-Step Dopamine Reset Protocol',
        'Environmental Cue-Elimination Architecture',
        'Cognitive Disruption & Urge-Surfing Frameworks',
      ],
    ),
    ProductModel(
      id: 'PROD-DM',
      slug: 'how-to-close-high-paying-clients-in-the-dms',
      title: 'How to Close High-Paying Clients in the DMs',
      description: 'Battle-tested direct messaging frameworks and objection scripts to turn cold social conversations into ₦150k - ₦500k client retainers.',
      priceNaira: 5000,
      regularPriceNaira: 25000,
      priceUsd: 15.0,
      regularPriceUsd: 40.0,
      category: 'Sales & Freelancing',
      benefits: [
        'Close 6-figure client contracts without awkward phone calls',
        'Achieve 80%+ response rates on cold outreach messages',
        'Never get ghosted again after quoting your rates',
      ],
      features: [
        'Copy-paste opening DM sequences for LinkedIn, Instagram, and X',
        'The Permission Close objection handling formula',
        'Exact pricing anchor presentation scripts',
      ],
    ),
    ProductModel(
      id: 'PROD-BOSS',
      slug: 'what-to-do-when-your-boss-is-angry-with-you',
      title: 'What to Do When Your Boss Is Angry With You',
      description: 'The executive survival playbook to de-escalate workplace conflict, disarm managerial hostility, protect your reputation, and turn crisis into leverage.',
      priceNaira: 5000,
      regularPriceNaira: 20000,
      priceUsd: 15.0,
      regularPriceUsd: 40.0,
      category: 'Career Acceleration',
      benefits: [
        'Neutralize managerial anger within 10 minutes without appearing submissive',
        'Document workplace interactions to create bulletproof protection',
        'Transform hostile confrontations into promotion leverage',
      ],
      features: [
        'The 4-Step Crisis De-escalation Protocol',
        'Email templates for post-conflict alignment and paper-trailing',
        'Power dynamics analysis and political defense playbook',
      ],
    ),
    ProductModel(
      id: 'PROD-BREAKUP',
      slug: 'what-to-do-after-a-breakup',
      title: 'What to Do After a Breakup',
      description: 'A tactical emotional reboot manual to stop rumination, eliminate obsessive checking, channel pain into physical/financial progress, and restore stoic clarity.',
      priceNaira: 5000,
      regularPriceNaira: 20000,
      priceUsd: 15.0,
      regularPriceUsd: 40.0,
      category: 'Mindset & Self-Mastery',
      benefits: [
        'Kill compulsive social media checking within 48 hours',
        'Channel emotional grief into physical training and financial output',
        'Rebuild masculine identity and self-worth from first principles',
      ],
      features: [
        'The Strict 30-Day Zero-Contact Architecture',
        'Dopamine stabilization and sleep restoration routine',
        'Cognitive re-anchoring thought audit exercises',
      ],
    ),
    ProductModel(
      id: 'PROD-IDEAS',
      slug: 'how-to-do-your-ideas',
      title: 'How to Do Your Ideas',
      description: 'The execution framework to overcome overthinking, validate concepts in 72 hours with zero capital, and ship projects to revenue.',
      priceNaira: 5000,
      regularPriceNaira: 20000,
      priceUsd: 15.0,
      regularPriceUsd: 40.0,
      category: 'Entrepreneurship & Strategy',
      benefits: [
        'Eliminate analysis paralysis and ship ideas in under 72 hours',
        'Validate market demand without building expensive software',
        'Collect pre-orders and cash flow before product completion',
      ],
      features: [
        'The 72-Hour Rapid Prototype Canvas',
        'Zero-Capital Customer Discovery Script',
        'Pre-Order Funnel Architecture',
      ],
    ),
  ];

  List<ProductModel> getProducts() => canonicalProducts;

  ProductModel? getProductBySlug(String slug) {
    try {
      return canonicalProducts.firstWhere((p) => p.slug == slug);
    } catch (_) {
      return null;
    }
  }
}
