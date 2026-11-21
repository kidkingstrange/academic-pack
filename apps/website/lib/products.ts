import { Product } from '@repo/api-contracts';

export const CANONICAL_PRODUCTS: Product[] = [
  {
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
      'Master the 2-Hour Active Recall Exam Cramming Protocol'
    ],
    features: [
      'The 7 Core Masterclass Manuals in DRM-free Digital PDF format',
      'Weekly Active Recall Spreadsheet Study Trackers',
      '52-Week Automated Academic Mastery Email Curriculum'
    ],
    targetAudience: 'University undergraduates, polytechnic students, and professional exam candidates.',
    coverImage: '/book cover home/3.png',
    isDeliverable: true,
    isBundle: true,
  },
  {
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
      'Eliminate brain fog, shame cycles, and social anxiety'
    ],
    features: [
      '21-Day Step-by-Step Dopamine Reset Protocol',
      'Environmental Cue-Elimination Architecture',
      'Cognitive Disruption & Urge-Surfing Frameworks'
    ],
    tagline: 'Stop fighting yourself. Break the loop forever.',
    painPoints: [
      "Swearing 'this is the last time', only to relapse 48 hours later when alone, bored, or stressed.",
      'Persistent brain fog, sluggish memory, and inability to focus on technical coursework or business.',
      'Social awkwardness, eye-contact avoidance, and loss of authentic masculine self-confidence.',
      'The streak counter trap where one 3-minute lapse triggers a multi-day binge.',
      'Toxic post-nut guilt, shame, and exhaustion that drains your natural drive.'
    ],
    chapters: [
      { number: '01', title: 'The Dopamine Architecture', summary: 'How high-speed digital novelty hijacks primitive reward circuits, desensitizes D2 receptors, and produces emotional apathy.' },
      { number: '02', title: 'The Trigger Loop Deconstruction', summary: 'Isolating the subtle physical, emotional, and digital cues that trigger automatic hand-to-groin habits.' },
      { number: '03', title: 'Environmental Engineering & Digital Sanitation', summary: 'Hardening your physical bedroom, phone, and laptop setups so willpower is never your primary defense.' },
      { number: '04', title: 'The Urge-Surfing Neural Protocol', summary: 'A 90-second visceral technique to observe intense dopamine cravings without acting on them until they dissolve.' },
      { number: '05', title: 'Relapse Inoculation & Chaser Prevention', summary: 'Neutralizing the chaser effect immediately if a slip occurs, preventing a minor lapse from becoming a multi-day binge.' },
      { number: '06', title: 'Biological Drive Transmutation', summary: 'Channeling raw sexual energy into high-yield academic performance, physical strength, and entrepreneurial output.' },
      { number: '07', title: 'Endocrine Recovery & Physical Vitality', summary: 'Evidence-based protocols to rapidly accelerate androgen sensitivity, sleep quality, and sovereign presence.' },
      { number: '08', title: 'Sovereign Self-Respect & The New Standard', summary: 'Permanently shedding the addict identity and adopting the internal operating system of an undisrupted man.' }
    ],
    faqs: [
      { question: 'Is this book based on religious shame or neuroscience?', answer: 'It is 100% grounded in cognitive behavioral psychology, endocrinology, and neurobiology. There are no shame-based guilt trips — only actionable neurological protocols.' },
      { question: 'How quickly does the brain fog lift after starting?', answer: 'Most readers report noticeable mental clarity and improved verbal fluency within 7 to 10 days of dopamine recalibration.' },
      { question: 'How do I access the book after paying ₦5,000?', answer: 'Instant download access is granted immediately on screen and dispatched to your email, with permanent access saved in your student digital library.' }
    ],
    targetAudience: 'Men seeking total freedom from compulsive habits and restored drive.',
    coverImage: '/book cover home/quitting-the-handjob.png',
    isDeliverable: true,
  },
  {
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
      'Never get ghosted again after quoting your rates'
    ],
    features: [
      'Copy-paste opening DM sequences for LinkedIn, Instagram, and X',
      'The Permission Close objection handling formula',
      'Exact pricing anchor presentation scripts'
    ],
    targetAudience: 'Freelancers, agency founders, consultants, and copywriters.',
    coverImage: '/book cover home/5.png',
    isDeliverable: true,
  },
  {
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
      'Transform hostile confrontations into promotion leverage'
    ],
    features: [
      'The 4-Step Crisis De-escalation Protocol',
      'Email templates for post-conflict alignment and paper-trailing',
      'Power dynamics analysis and political defense playbook'
    ],
    targetAudience: 'Corporate professionals, managers, and remote workers.',
    coverImage: '/book cover home/4.png',
    isDeliverable: true,
  },
  {
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
      'Rebuild masculine identity and self-worth from first principles'
    ],
    features: [
      'The Strict 30-Day Zero-Contact Architecture',
      'Dopamine stabilization and sleep restoration routine',
      'Cognitive re-anchoring thought audit exercises'
    ],
    targetAudience: 'Anyone navigating painful relationship dissolution.',
    coverImage: '/book cover home/2.png',
    isDeliverable: true,
  },
  {
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
      'Collect pre-orders and cash flow before product completion'
    ],
    features: [
      'The 72-Hour Rapid Prototype Canvas',
      'Zero-Capital Customer Discovery Script',
      'Pre-Order Funnel Architecture'
    ],
    targetAudience: 'Aspiring founders, creators, and professionals with unlaunched ideas.',
    coverImage: '/book cover home/1.png',
    isDeliverable: true,
  },
  {
    id: 'PROD-HARD',
    slug: 'get-good-at-hard-things',
    title: 'Get Good at Hard Things',
    description: 'A systematic methodology for deconstructing difficult subjects, building cognitive stamina, and mastering intimidating skills.',
    priceNaira: 5000,
    regularPriceNaira: 20000,
    priceUsd: 15.0,
    regularPriceUsd: 40.0,
    category: 'Academics & Study Skills',
    benefits: [
      'Master dense mathematical or technical material without getting overwhelmed',
      'Build 4+ hours of uninterrupted deep cognitive focus',
      'Rapidly deconstruct unfamiliar intellectual concepts'
    ],
    features: [
      'The First-Principles Chunking Framework',
      'Deliberate Practice Feedback Loop Templates',
      'Cognitive Stamina Conditioning Protocol'
    ],
    targetAudience: 'STEM students, engineers, developers, and analytical learners.',
    coverImage: '/book cover home/get-good-at-hard-things.png',
    isDeliverable: true,
  }
];

export function getProductBySlug(slug: string): Product | undefined {
  return CANONICAL_PRODUCTS.find((p) => p.slug === slug);
}
