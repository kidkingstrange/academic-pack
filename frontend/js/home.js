/**
 * Multi-Book Homepage Logic — Catalog, Search, Filtering, Book Details Modal & Conversion Management
 */
const API_BASE = '/api';

const BOOKS = [
  {
    id: "how-to-close-high-paying-clients-in-the-dms",
    title: "How to Close High-Paying Clients in the DMs",
    cover: "/assets/covers/how-to-close-high-paying-clients-in-the-dms.webp",
    category: "Sales & Marketing",
    rating: 4.9,
    reviews: 214,
    description: "The complete script, objection handling, and conversation framework to close high-ticket deals inside social media DMs.",
    painPoints: [
      "Getting left on 'read' after sending your price or proposal",
      "Spending hours chatting with clients who end up saying 'I can't afford this'",
      "Feeling uncomfortable or needy when pitching high-ticket offers"
    ],
    solutionOverview: "This playbook gives you exact word-for-word DM conversation scripts that build instant authority, qualify client budgets upfront, and lead prospects naturally to say YES without aggressive selling.",
    whoShouldReadThis: "Freelancers, Agency Founders, Consultants, Service Providers, and Digital Creators selling offers above ₦ 50,000.",
    bullets: [
      "Copy-paste DM opening scripts that get 80%+ response rates",
      "Overcoming the 'It's too expensive' objection effortlessly",
      "Transitioning from casual conversation to a 5-figure retainer",
      "The budget-qualification question to ask before sending any proposal"
    ]
  },
  {
    id: "how-to-build-a-high-converting-whatsapp",
    title: "How to Build a High-Converting WhatsApp Sales Funnel",
    cover: "/assets/covers/how-to-build-a-high-converting-whatsapp.webp",
    category: "Sales & Marketing",
    rating: 4.9,
    reviews: 189,
    description: "Turn your WhatsApp broadcast and status into an automated sales machine that converts cold leads into eager buyers.",
    painPoints: [
      "Posting WhatsApp status updates daily with zero sales or replies",
      "Losing contacts because you don't have an automated lead capture system",
      "Low broadcast view rates and audience fatigue from spammy messaging"
    ],
    solutionOverview: "Discover the exact WhatsApp broadcast sequence and status copywriting formula that builds buying desire on autopilot and converts viewers into daily paying customers.",
    whoShouldReadThis: "E-commerce sellers, course creators, digital marketers, and business owners leveraging WhatsApp for daily sales.",
    bullets: [
      "Broadcast sequence structure for instant daily sales",
      "Status copywriting formula that builds buying intent",
      "Automating contact saving & lead capture on WhatsApp",
      "The 3-post Status Formula that generates daily incoming payment alerts"
    ]
  },
  {
    id: "how-to-sell-digital-products-globally",
    title: "How to Sell Digital Products Globally",
    cover: "/assets/covers/how-to-sell-digital-products-globally.webp",
    category: "Sales & Marketing",
    rating: 4.8,
    reviews: 165,
    description: "Frameworks for building, pricing, and distributing digital products to international buyers from Nigeria.",
    painPoints: [
      "Stuck earning only local currency while inflation erodes your profit margins",
      "Payment gateway rejections when trying to accept USD, EUR, or GBP online",
      "Not knowing how to target foreign buyers in the US, UK, Canada, and Europe"
    ],
    solutionOverview: "Learn the end-to-end framework for launching digital products priced in foreign currencies, setting up seamless multi-currency checkout, and attracting global buyers.",
    whoShouldReadThis: "Digital creators, authors, educators, and service providers who want to earn foreign currency from home.",
    bullets: [
      "Setting up multi-currency international Paystack checkout",
      "Targeting buyers in US, UK, Canada & Europe with high purchasing power",
      "Pricing digital products in USD and EUR for maximum margin",
      "Legal and tax setup for borderless digital product sales"
    ]
  },
  {
    id: "naira-ads",
    title: "Naira Ads Masterclass: Scale Your Business with Meta Ads",
    cover: "/assets/covers/naira-ads.webp",
    category: "Sales & Marketing",
    rating: 4.9,
    reviews: 310,
    description: "Run profitable Facebook and Instagram ads using Naira accounts without ban risks or payment failures.",
    painPoints: [
      "Constant Meta ad account bans, disabled payment methods, and dollar card declines",
      "Wasting daily ad spend on low-quality leads who never buy",
      "High cost-per-lead and low ROAS eating up your business profits"
    ],
    solutionOverview: "A tactical guide to setting up unbanable Naira ad accounts on Meta, creating high-converting ad copy and visuals, and scaling daily ad spend profitably.",
    whoShouldReadThis: "Business owners, media buyers, agency founders, and marketers running Meta ads in Nigeria.",
    bullets: [
      "Setting up ban-proof Naira ad accounts on Meta",
      "High-ROAS creative templates for local and global audiences",
      "Scaling daily ad spend while staying profitable",
      "Fixing disabled ad accounts and avoiding policy triggers"
    ]
  },
  {
    id: "how-to-land-high-paying-corporate-clients",
    title: "How to Land High-Paying Corporate Clients",
    cover: "/assets/covers/how-to-land-high-paying-corporate-clients.webp",
    category: "Sales & Marketing",
    rating: 4.9,
    reviews: 142,
    description: "Position yourself, pitch decision-makers, and win high-retainer B2B corporate contracts.",
    painPoints: [
      "Stuck pitching small businesses with tight budgets and endless demands",
      "Gatekeepers blocking you from executive decision-makers at top companies",
      "Submitting long proposal documents that get ignored or shelved for months"
    ],
    solutionOverview: "Master the B2B corporate sales strategy: how to identify decision-makers, pitch 7-figure retainer contracts, and close corporate deals with speed.",
    whoShouldReadThis: "B2B service providers, consultants, corporate trainers, software vendors, and agency founders.",
    bullets: [
      "Finding and reaching executive decision-makers directly",
      "Writing winning B2B proposal decks that close fast",
      "Structuring annual retainer agreements with 7-figure scope",
      "Navigating corporate procurement and payment terms"
    ]
  },
  {
    id: "how-to-build-a-business-that-functions-without",
    title: "How to Build a Business That Functions Without You",
    cover: "/assets/covers/how-to-build-a-business-that-functions-without.webp",
    category: "Business & Scale",
    rating: 4.9,
    reviews: 178,
    description: "Systematize operations, delegate responsibilities, and create SOPs so your business runs smoothly when you step away.",
    painPoints: [
      "Working 14-hour days because your team cannot execute without your constant supervision",
      "Business operations collapsing the moment you take a weekend off or travel",
      "Being the bottleneck in every decision, customer issue, and daily task"
    ],
    solutionOverview: "Step-by-step operational blueprint for documenting SOPs, building accountable management structures, and stepping into the true CEO role.",
    whoShouldReadThis: "Founders, business owners, and operators overwhelmed by daily execution bottlenecks.",
    bullets: [
      "Creating step-by-step SOPs your team actually follows",
      "Hiring & training reliable operations managers",
      "Removing yourself from daily execution bottleneck",
      "Key operational metrics to monitor performance remotely"
    ]
  },
  {
    id: "how-to-fund-your-business-with-upfront",
    title: "How to Fund Your Business with Upfront Client Cash",
    cover: "/assets/covers/how-to-fund-your-business-with-upfront.webp",
    category: "Business & Scale",
    rating: 4.8,
    reviews: 129,
    description: "Bootstrapping playbook to pre-sell services and fund expansion using upfront client payments instead of debt.",
    painPoints: [
      "Turning down high-value projects due to lack of working capital",
      "Taking high-interest loans to fund operations and inventory",
      "Delivering work for clients who delay payment for 60 to 90 days"
    ],
    solutionOverview: "Learn pre-selling strategies and contract structures that get clients to pay 50% to 100% upfront, funding your business growth with customer revenue.",
    whoShouldReadThis: "Bootstrapped founders, service agency owners, project managers, and product creators.",
    bullets: [
      "Pre-selling new services before building them",
      "Securing 50%–100% upfront deposits on custom projects",
      "Cash flow preservation systems for fast-growing companies",
      "De-risking new product launches with pre-orders"
    ]
  },
  {
    id: "how-to-maintain-positive-cash-flow-under",
    title: "How to Maintain Positive Cash Flow Under Pressure",
    cover: "/assets/covers/how-to-maintain-positive-cash-flow-under.webp",
    category: "Business & Scale",
    rating: 4.8,
    reviews: 115,
    description: "Cash flow management strategies for volatile markets, inflation, and unpredictable revenue cycles.",
    painPoints: [
      "Monthly panic over payroll, rent, and vendor bills during slow sales cycles",
      "Currency devaluation eating up your profit margins before you can reinvest",
      "Unplanned operational expenses wiping out business bank balances"
    ],
    solutionOverview: "A financial survival playbook: build a 6-month operational cash reserve, manage receivables, and insulate your company against economic volatility.",
    whoShouldReadThis: "Business owners, CFOs, financial managers, and entrepreneurs in high-inflation markets.",
    bullets: [
      "Building a 6-month operational cash reserve buffer",
      "Hedging against FX devaluation and rising expenses",
      "Managing receivables to eliminate late customer payments",
      "Dynamic pricing adjustments for inflation control"
    ]
  },
  {
    id: "how-to-qualify-and-filter-out-low",
    title: "How to Qualify and Filter Out Low-Paying Clients",
    cover: "/assets/covers/how-to-qualify-and-filter-out-low.webp",
    category: "Business & Scale",
    rating: 4.9,
    reviews: 154,
    description: "Stop wasting time on budget-constrained clients and establish qualifying filters that attract premium buyers.",
    painPoints: [
      "Dealing with demanding, low-paying clients who take up 90% of your energy",
      "Spending hours on free discovery calls only to discover the client has no budget",
      "Scope creep and micromanagement from discount-seeking customers"
    ],
    solutionOverview: "Establish strict qualification gates and application forms that filter out price-sensitive prospects and position you as a high-value expert.",
    whoShouldReadThis: "Freelancers, consultants, agency owners, and service professionals tired of cheap clients.",
    bullets: [
      "Red-flag client identification in the first 5 minutes",
      "Application forms that filter out price shoppers",
      "Polite scripts to decline bad-fit clients gracefully",
      "Establishing minimum engagement thresholds for high margins"
    ]
  },
  {
    id: "how-to-stop-worrying-about-money",
    title: "How to Stop Worrying About Money & Build Security",
    cover: "/assets/covers/how-to-stop-worrying-about-money.webp",
    category: "Business & Wealth",
    rating: 4.9,
    reviews: 201,
    description: "Psychological principles and tactical money management systems to eliminate financial anxiety.",
    painPoints: [
      "Constant knot in your stomach about monthly bills and future stability",
      "Earning money but watching it disappear with no clear savings system",
      "Fear of taking financial risks because you lack a safety net"
    ],
    solutionOverview: "Rebuild your relationship with money through automated personal wealth systems, emergency fund allocation rules, and long-term security habits.",
    whoShouldReadThis: "High earners, entrepreneurs, freelancers, and professionals seeking financial peace.",
    bullets: [
      "Automating personal savings and emergency funds",
      "Decoupling stress from monthly income fluctuations",
      "Building predictable long-term financial security",
      "The 3-tier wealth preservation matrix"
    ]
  },
  {
    id: "how-to-transition-from-a-side-hustle-to",
    title: "How to Transition from a Side Hustle to Full-Time Enterprise",
    cover: "/assets/covers/how-to-transition-from-a-side-hustle-to.webp",
    category: "Business & Scale",
    rating: 4.9,
    reviews: 167,
    description: "Risk-calculated roadmap for quitting your 9-to-5 safely and scaling your business full-time.",
    painPoints: [
      "Exhausted from working a 9-to-5 while trying to build a business after hours",
      "Fear of quitting your job and running out of money in the first 90 days",
      "Unsure when your side hustle revenue is stable enough to make the leap"
    ],
    solutionOverview: "Calculated exit framework: calculate your safe runway, maintain job performance while building, and launch your business full-time with confidence.",
    whoShouldReadThis: "Side hustlers, 9-to-5 employees, aspiring full-time founders, and early-stage entrepreneurs.",
    bullets: [
      "Calculating your minimum safe exit revenue baseline",
      "Managing job performance while building your business after hours",
      "First 90 days full-time execution strategy",
      "Building a 6-month personal runway before handing in your notice"
    ]
  },
  {
    id: "how-to-ask-for-the-promotion-and",
    title: "How to Ask for the Promotion and Get It",
    cover: "/assets/covers/how-to-ask-for-the-promotion-and.webp",
    category: "Career Acceleration",
    rating: 4.9,
    reviews: 143,
    description: "Proven corporate negotiation scripts and performance proof frameworks to secure salary increases and titles.",
    painPoints: [
      "Passed over for promotions while less experienced colleagues advance",
      "Uncomfortable starting salary and title increase conversations with your boss",
      "Working hard without quantitative proof of your business impact"
    ],
    solutionOverview: "Corporate advancement system: build an undeniable proof sheet, time your review request, and use proven negotiation scripts to secure your raise.",
    whoShouldReadThis: "Corporate professionals, team leads, mid-level managers, and ambitious employees.",
    bullets: [
      "Building an undeniable 'Brag Sheet' of quantitative business wins",
      "Timing your raise request for maximum success probability",
      "Handling salary pushback and securing title progression",
      "Word-for-word scripts for performance review meetings"
    ]
  },
  {
    id: "how-to-get-seen-by-the-people-who-actually-decide",
    title: "How to Get Seen by the People Who Actually Decide Your Promotion",
    cover: "/assets/covers/how-to-get-seen-by-the-people-who-actually-decide.webp",
    category: "Career Acceleration",
    rating: 4.8,
    reviews: 138,
    description: "Strategic executive visibility tactics to make your work noticeable to senior leadership and key stakeholders.",
    painPoints: [
      "Doing great work in silence while senior leadership doesn't know who you are",
      "Stuck doing low-visibility administrative tasks that lead nowhere",
      "Unsure how to present to executive stakeholders without sounding arrogant"
    ],
    solutionOverview: "Master executive visibility: get assigned to high-impact strategic projects, present effectively to senior leaders, and build executive sponsorships.",
    whoShouldReadThis: "Ambitious corporate employees, project leaders, and professionals seeking executive recognition.",
    bullets: [
      "Getting assigned to high-visibility strategic projects",
      "Presenting effectively to C-suite decision-makers",
      "Building internal executive sponsorships across departments",
      "Converting behind-the-scenes work into high-level business impact"
    ]
  },
  {
    id: "how-to-expand-your-role-before-anyone",
    title: "How to Expand Your Role Before Anyone Asks",
    cover: "/assets/covers/how-to-expand-your-role-before-anyone.webp",
    category: "Career Acceleration",
    rating: 4.8,
    reviews: 119,
    description: "Proactive career ownership techniques to carve out high-impact responsibilities and fast-track advancement.",
    painPoints: [
      "Feeling trapped in a narrow, uninspiring job description",
      "Waiting for management to assign you higher-level strategic responsibilities",
      "Not knowing how to initiate new initiatives without stepping on toes"
    ],
    solutionOverview: "Proactive career framework: spot unaddressed company challenges, create new role responsibilities around your strengths, and accelerate promotion timelines.",
    whoShouldReadThis: "Self-driven professionals, specialists, and rising corporate leaders.",
    bullets: [
      "Identifying unaddressed company problems and solving them first",
      "Creating new role definitions tailored to your strengths",
      "Fast-tracking leadership recognition without waiting for permission",
      "Securing resources and approval for self-initiated projects"
    ]
  },
  {
    id: "how-to-master-your-role-so-well",
    title: "How to Master Your Role So Well You Become Irreplaceable",
    cover: "/assets/covers/how-to-master-your-role-so-well.webp",
    category: "Career Acceleration",
    rating: 4.9,
    reviews: 182,
    description: "Operational excellence and skill stack building to become an essential key player in any organization.",
    painPoints: [
      "Anxiety about corporate downsizing, restructuring, or job insecurity",
      "Feeling like your work could easily be outsourced or replaced by AI",
      "Struggling to maintain top-tier output speed and consistency"
    ],
    solutionOverview: "Develop unique domain mastery, high-speed execution workflows, and specialized skill stacks that make you indispensably valuable.",
    whoShouldReadThis: "Key employees, department leads, specialists, and professionals seeking job security.",
    bullets: [
      "Developing niche domain expertise no one else possesses",
      "Optimized speed and quality output frameworks",
      "Protecting your position against downsizing and restructuring",
      "Building a multi-skilled competitive moat in your industry"
    ]
  },
  {
    id: "how-to-navigate-the-unspoken-rules-and",
    title: "How to Navigate the Unspoken Rules of Workplace Politics",
    cover: "/assets/covers/how-to-navigate-the-unspoken-rules-and.webp",
    category: "Career Acceleration",
    rating: 4.9,
    reviews: 176,
    description: "Corporate dynamics, alliance building, and self-preservation in competitive office environments.",
    painPoints: [
      "Blindsided by office drama, hidden agendas, and toxic department rivalries",
      "Watching colleagues steal credit for your hard work and ideas",
      "Struggling to build cross-departmental influence without being political"
    ],
    solutionOverview: "Ethical office diplomacy guide: map workplace power structures, protect your work credit, and build strategic alliances that safeguard your career.",
    whoShouldReadThis: "Corporate workers, managers, team members, and executives in large organizations.",
    bullets: [
      "Mapping power structures and hidden decision alliances",
      "Protecting your credit and ideas from credit stealers",
      "Ethical office diplomacy that accelerates career growth",
      "Defusing workplace conflict and navigating difficult colleagues"
    ]
  },
  {
    id: "how-to-think-like-a-leader-before-you-have",
    title: "How to Think Like a Leader Before You Have the Title",
    cover: "/assets/covers/how-to-think-like-a-leader-before-you-have.webp",
    category: "Career Acceleration",
    rating: 4.9,
    reviews: 160,
    description: "Strategic leadership mindset, decision-making frameworks, and influence building for aspiring executives.",
    painPoints: [
      "Stuck in a task-completion mindset instead of strategic business thinking",
      "Unsure how to influence peers and lead projects without formal authority",
      "Hesitating when required to make high-stakes operational decisions"
    ],
    solutionOverview: "Executive decision framework: shift from task execution to ROI thinking, lead peers effectively, and demonstrate executive readiness.",
    whoShouldReadThis: "Aspiring managers, senior specialists, team leads, and future executives.",
    bullets: [
      "Thinking in company ROI rather than task completion",
      "Leading peers and cross-functional teams with authority",
      "Executive decision-making under uncertainty",
      "Developing strategic foresight and problem-prevention skills"
    ]
  },
  {
    id: "how-to-turn-your-boss-into-your-biggest",
    title: "How to Turn Your Boss Into Your Biggest Career Advocate",
    cover: "/assets/covers/how-to-turn-your-boss-into-your-biggest.webp",
    category: "Career Acceleration",
    rating: 4.8,
    reviews: 145,
    description: "Managing up, aligning goals, and turning your direct manager into your active sponsor.",
    painPoints: [
      "Struggling with a distant, demanding, or micromanaging boss",
      "Misaligned expectations causing friction in 1-on-1 performance meetings",
      "Feeling like your manager does not actively push for your advancement"
    ],
    solutionOverview: "Managing-up masterclass: align your daily execution with your boss's top KPIs, conduct strategic 1-on-1s, and build strong executive sponsorship.",
    whoShouldReadThis: "Employees at all corporate levels wanting a better relationship with management.",
    bullets: [
      "Aligning your daily work with your manager's top KPIs",
      "Conducting high-impact 1-on-1 career alignment meetings",
      "Turning difficult managers into helpful career sponsors",
      "Proactive status reporting that builds complete trust"
    ]
  },
  {
    id: "how-to-heal-your-body-from-stress",
    title: "How to Heal Your Body from Chronic Stress & Burnout",
    cover: "/assets/covers/how-to-heal-your-body-from-stress.webp",
    category: "Mindset & Health",
    rating: 4.9,
    reviews: 210,
    description: "Somatic recovery techniques and energy management for high achievers facing burnout.",
    painPoints: [
      "Waking up exhausted, relying on caffeine, and feeling physically drained daily",
      "Brain fog, chronic anxiety, and inability to switch off work at night",
      "Experiencing physical burnout symptoms like headaches, tension, and insomnia"
    ],
    solutionOverview: "Somatic recovery protocol: reset over-stimulated cortisol levels, restore deep sleep architecture, and rebuild daily energy stamina.",
    whoShouldReadThis: "Overworked entrepreneurs, corporate executives, founders, and high achievers.",
    bullets: [
      "Lowering cortisol and nervous system over-arousal",
      "Restoring deep sleep and physical stamina",
      "Building high-output routines without exhausting your body",
      "Somatic nervous system reset exercises for immediate calm"
    ]
  },
  {
    id: "how-to-overcome-decision-paralysis",
    title: "How to Overcome Decision Paralysis and Take Action",
    cover: "/assets/covers/how-to-overcome-decision-paralysis.webp",
    category: "Mindset & Health",
    rating: 4.9,
    reviews: 194,
    description: "Frameworks to eliminate overthinking, reduce analysis paralysis, and execute with confidence.",
    painPoints: [
      "Spending weeks overanalyzing decisions without taking concrete action",
      "Fear of making the wrong choice keeping you stuck in place",
      "Starting multiple projects but abandoning them due to doubt"
    ],
    solutionOverview: "Bias-to-action methodology: implement the 5-minute decision rule, eliminate fear of failure, and build unstoppable execution momentum.",
    whoShouldReadThis: "Overthinkers, perfectionists, founders, students, and creators stuck in planning loops.",
    bullets: [
      "The 5-minute bias-to-action rule for complex decisions",
      "Eliminating fear of making wrong choices",
      "Daily execution systems that replace motivation dependency",
      "Reversible vs. irreversible decision framework"
    ]
  },
  {
    id: "how-to-set-boundaries-with-family",
    title: "How to Set Boundaries with Family, Money, and Time",
    cover: "/assets/covers/how-to-set-boundaries-with-family.webp",
    category: "Mindset & Health",
    rating: 4.9,
    reviews: 228,
    description: "Assertive communication and emotional boundary setting to protect your focus, energy, and finances.",
    painPoints: [
      "Feeling guilty saying NO to financial demands from family and friends",
      "Constant interruptions ruining your deep-work focus hours",
      "Drained by emotionally demanding relationships that pull you away from your goals"
    ],
    solutionOverview: "Assertive communication playbook: establish clear financial, personal, and work boundaries guilt-free using proven conversation scripts.",
    whoShouldReadThis: "High earners, founders, professionals, and individuals managing family demands.",
    bullets: [
      "Saying NO to financial demands guilt-free",
      "Protecting deep-work focus hours from family interruptions",
      "Scripts for handling difficult personal conversations",
      "Establishing healthy financial separation boundaries"
    ]
  },
  {
    id: "how-to-stay-calm-in-chaos",
    title: "How to Stay Calm in Chaos and High-Pressure Environments",
    cover: "/assets/covers/how-to-stay-calm-in-chaos.webp",
    category: "Mindset & Health",
    rating: 4.8,
    reviews: 165,
    description: "Stoic mental models and emotional regulation techniques for high-stakes pressure situations.",
    painPoints: [
      "Panicking or losing emotional control when sudden crises hit",
      "Making impulsive mistakes during high-stakes pressure moments",
      "Carrying work stress and anxiety home every evening"
    ],
    solutionOverview: "High-pressure mental armor: master real-time physiological calm protocols, objective decision-making under crisis, and Stoic clarity.",
    whoShouldReadThis: "Leaders, founders, emergency responders, traders, and high-stress professionals.",
    bullets: [
      "Instant physiological calm techniques under sudden crisis",
      "Maintaining objective clarity when stakes are extremely high",
      "Developing an unshakeable mental armor",
      "Compartmentalizing high-stress events without emotional burn"
    ]
  },
  {
    id: "how-to-stop-learning-and-start-executing",
    title: "How to Stop Learning and Start Executing Today",
    cover: "/assets/covers/how-to-stop-learning-and-start-executing.webp",
    category: "Mindset & Health",
    rating: 4.9,
    reviews: 245,
    description: "Break the cycle of endless tutorials and course hoarding — switch to active output and real-world results.",
    painPoints: [
      "Buying dozens of courses and books without applying what you read",
      "Feeling like you need 'one more certification' before taking real action",
      "Trapped in tutorial hell while others with less knowledge build real assets"
    ],
    solutionOverview: "Action conversion protocol: transition from passive consumption to active output using the 80/20 execution ratio and immediate revenue milestones.",
    whoShouldReadThis: "Course hoarders, perpetual students, aspiring entrepreneurs, and skill builders.",
    bullets: [
      "Breaking tutorial hell and passive learning addiction",
      "Converting knowledge into immediate cash flow output",
      "The 80/20 execution ratio for rapid skill mastery",
      "Building real-world projects instead of collecting certificates"
    ]
  },
  {
    id: "book1",
    title: "How to Balance Your Academics and Your Business",
    cover: "/assets/covers/book1.webp",
    category: "Education & Mastery",
    rating: 4.9,
    reviews: 580,
    description: "A practical guide to excelling in school, growing your business, and building the life you want without burnout.",
    painPoints: [
      "Failing coursework because business operations consume all your time",
      "Sacrificing business growth during exam season due to poor time planning",
      "Constant exhaustion trying to manage lectures, client orders, and study sessions"
    ],
    solutionOverview: "Student-founder time allocation playbook: build structured weekly study & business blocks, automate routine tasks, and maintain top grades while scaling revenue.",
    whoShouldReadThis: "Student entrepreneurs, side-hustle students, and young founders in school.",
    bullets: [
      "Time allocation framework for student founders",
      "Prioritizing coursework while running a business",
      "Managing stress and maintaining top academic performance",
      "Exam-season business automation checklist"
    ]
  },
  {
    id: "book2",
    title: "How to Score High in Any Exam",
    cover: "/assets/covers/book2.webp",
    category: "Education & Mastery",
    rating: 4.9,
    reviews: 310,
    description: "Proven strategies, smart study techniques, and practical exam preparation protocols to achieve top results.",
    painPoints: [
      "Studying for 10 hours a day only to blank out inside the examination hall",
      "Last-minute cramming causing high anxiety and poor test scores",
      "Struggling to retain vast syllabus volumes across multiple difficult courses"
    ],
    solutionOverview: "Exam score optimization system: active recall schedules, past question deconstruction, and exam hall execution tactics to score top grades.",
    whoShouldReadThis: "Students, professional certification candidates, and exam takers aiming for A's.",
    bullets: [
      "Active recall & spaced repetition study schedule",
      "Deconstructing exam questions for maximum marks",
      "Eliminating exam anxiety & last-minute cramming",
      "The 3-pass examination hall time management system"
    ]
  },
  {
    id: "book3",
    title: "Result-Oriented Learning",
    cover: "/assets/covers/book3.webp",
    category: "Education & Mastery",
    rating: 4.9,
    reviews: 275,
    description: "Know exactly what to study for exams. Eliminate wasted effort and focus on high-yield topic mastery.",
    painPoints: [
      "Wasting effort reading entire textbooks cover-to-cover without knowing what examiners test",
      "Struggling to understand complex academic concepts and formulas",
      "Spending weeks studying with very little long-term memory retention"
    ],
    solutionOverview: "High-yield study methodology: identify high-yield exam patterns, apply the Feynman comprehension technique, and study half the hours with double retention.",
    whoShouldReadThis: "Students wanting maximum academic grades with minimal wasted study time.",
    bullets: [
      "Identifying high-yield exam topics & past question trends",
      "Feynman technique for rapid concept comprehension",
      "Studying less hours while achieving higher retention",
      "Summary synthesis templates for fast pre-exam review"
    ]
  },
  {
    id: "book4",
    title: "Get Good at Hard Things",
    cover: "/assets/covers/book4.webp",
    category: "Education & Mastery",
    rating: 4.8,
    reviews: 190,
    description: "A system for academic and skill excellence through discipline, mental depth, and deliberate effort.",
    painPoints: [
      "Giving up on complex subjects (Math, Coding, Science, Finance) because they feel too hard",
      "Short attention span making it impossible to sit and study for more than 20 minutes",
      "Cognitive frustration when encountering difficult problems"
    ],
    solutionOverview: "Deliberate practice protocol: build 4-hour deep focus stamina, embrace cognitive friction, and master difficult technical subjects rapidly.",
    whoShouldReadThis: "Students, coders, engineers, analysts, and anyone tackling hard technical subjects.",
    bullets: [
      "Deliberate practice protocol for difficult subjects",
      "Building 4-hour deep focus stamina",
      "Overcoming frustration & cognitive fatigue",
      "Breaking complex topics into simple foundational building blocks"
    ]
  },
  {
    id: "book5",
    title: "30-Day Study Tracker",
    cover: "/assets/covers/book5.webp",
    category: "Education & Mastery",
    rating: 4.9,
    reviews: 230,
    description: "Daily progress & discipline system to build consistent study habits, track syllabus coverage, and stay accountable.",
    painPoints: [
      "Procrastinating until 3 days before major exams",
      "Losing track of how much syllabus content is left to review",
      "Inconsistent daily study habits leading to panic and poor grades"
    ],
    solutionOverview: "30-day discipline blueprint: visual syllabus tracker, daily milestone logs, and habit consistency grids that guarantee exam readiness.",
    whoShouldReadThis: "Students and professional candidates preparing for major upcoming exams.",
    bullets: [
      "Daily habit tracking grid for 30-day exam prep",
      "Measuring daily topic completion & review milestones",
      "Building unshakeable consistency and study momentum",
      "Visual syllabus coverage matrix for zero surprise exam topics"
    ]
  },
  {
    id: "book6",
    title: "Focus Template: Deep Work Protocol",
    cover: "/assets/covers/book6.webp",
    category: "Mindset & Health",
    rating: 4.9,
    reviews: 215,
    description: "Deep work & distraction elimination system to block out digital noise, build focus stamina, and double study output.",
    painPoints: [
      "Constantly checking Instagram, WhatsApp, and TikTok every 5 minutes while working",
      "Taking 4 hours to finish a task that should take 45 minutes",
      "Feeling mentally scattered and unable to enter deep flow states"
    ],
    solutionOverview: "Distraction elimination protocol: optimize your digital workspace, run structured deep-work sprints, and restore sharp mental clarity.",
    whoShouldReadThis: "Remote workers, creators, students, and professionals struggling with screen addiction.",
    bullets: [
      "Digital environment distraction elimination framework",
      "Structured Pomodoro & deep work sprint blocks",
      "Restoring mental clarity and focus control",
      "Social media blocking & attention recovery protocols"
    ]
  },
  {
    id: "book7",
    title: "Exam Survival Guide",
    cover: "/assets/covers/book7.webp",
    category: "Education & Mastery",
    rating: 4.9,
    reviews: 340,
    description: "High-stakes preparation & tactical performance protocol for final exams, professional certifications, and tests.",
    painPoints: [
      "Panic and severe anxiety in the 48 hours leading up to an exam",
      "Running out of time inside the examination hall with unanswered questions",
      "Freezing up when facing unfamiliar or tricky exam questions"
    ],
    solutionOverview: "Emergency exam preparation: 48-hour emergency review protocol, examination hall pacing tactics, and emergency question recovery strategies.",
    whoShouldReadThis: "Final year students, professional exam candidates (ICAN, GRE, ACCA), and test takers.",
    bullets: [
      "48-hour pre-exam emergency review protocol",
      "Pacing strategies inside the examination hall",
      "Handling unexpected questions under severe time pressure",
      "Physiological anxiety control techniques before entering the hall"
    ]
  }
];

let selectedBook = null;
let currentCategory = 'all';
let searchQuery = '';

document.addEventListener('DOMContentLoaded', () => {
  // Capture affiliate code from URL if present
  const urlParams = new URLSearchParams(window.location.search);
  const refCode = urlParams.get('ref');
  if (refCode) {
    try { localStorage.setItem('ac_referral_code', refCode.trim().toUpperCase()); } catch(e){}
  }

  checkOwnedState();
  renderBooks();
  checkSuccessState();
  setupSearchListener();
});

function getOwnedBooks() {
  try {
    const raw = localStorage.getItem('scale_owned_books');
    return raw ? JSON.parse(raw) : [];
  } catch(e) {
    return [];
  }
}

function addOwnedBook(bookId) {
  const owned = getOwnedBooks();
  if (!owned.includes(bookId)) {
    owned.push(bookId);
    try { localStorage.setItem('scale_owned_books', JSON.stringify(owned)); } catch(e){}
  }
}

function checkOwnedState() {
  const owned = getOwnedBooks();
  const banner = document.getElementById('returning-visitor-banner');
  const countEl = document.getElementById('owned-count-display');
  if (owned.length > 0 && banner && countEl) {
    countEl.textContent = owned.length;
    banner.style.display = 'flex';
  }
}

function filterCategory(catKey, btnEl) {
  currentCategory = catKey;
  document.querySelectorAll('.filter-tab').forEach(b => {
    b.classList.remove('active');
    b.blur();
  });

  if (btnEl) {
    btnEl.classList.add('active');
  } else {
    const target = document.querySelector(`.filter-tab[data-category="${catKey}"]`);
    if (target) target.classList.add('active');
  }

  renderBooks();
}

function matchesCategoryFilter(bookCategory, targetKey) {
  if (!targetKey || targetKey === 'all') return true;
  const bc = bookCategory.toLowerCase();
  const tk = targetKey.toLowerCase();
  if (tk === 'sales') return bc.includes('sales') || bc.includes('marketing');
  if (tk === 'business') return bc.includes('business') || bc.includes('scale') || bc.includes('finance') || bc.includes('wealth');
  if (tk === 'career') return bc.includes('career');
  if (tk === 'mindset') return bc.includes('mindset') || bc.includes('health');
  if (tk === 'education') return bc.includes('education') || bc.includes('mastery');
  return bc.includes(tk);
}

function setupSearchListener() {
  const input = document.getElementById('catalog-search-input');
  if (!input) return;
  input.addEventListener('input', (e) => {
    searchQuery = e.target.value.trim().toLowerCase();
    renderBooks();
  });
}

function renderBooks() {
  const grid = document.getElementById('books-grid');
  if (!grid) return;

  const ownedBooks = getOwnedBooks();

  const filtered = BOOKS.filter(book => {
    const matchesCat = matchesCategoryFilter(book.category, currentCategory);
    const matchesSearch = !searchQuery || 
      book.title.toLowerCase().includes(searchQuery) || 
      book.description.toLowerCase().includes(searchQuery) ||
      book.category.toLowerCase().includes(searchQuery);
    return matchesCat && matchesSearch;
  });

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
        <i class="bi bi-search" style="font-size: 2.5rem; color: var(--gold); display: block; margin-bottom: 12px;"></i>
        <h3 style="color: #fff; margin-bottom: 8px;">No masterclasses found</h3>
        <p>Try searching for a different skill or goal, or select 'All Categories'.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map((book, idx) => {
    const isAboveTheFold = idx < 6;
    const loadingAttr = isAboveTheFold ? 'loading="eager" fetchpriority="high"' : 'loading="lazy"';
    const isOwned = ownedBooks.includes(book.id);

    const badgeHtml = isOwned 
      ? `<div class="book-card__badge book-card__badge--owned"><i class="bi bi-check-circle-fill"></i> In Library</div>`
      : `<div class="book-card__badge">Available Now</div>`;

    const buttonHtml = isOwned
      ? `<button class="btn btn--green book-card__btn" onclick="event.stopPropagation(); location.href='/library'">Read Now</button>`
      : `<button class="btn btn--gold book-card__btn" onclick="event.stopPropagation(); openPreorderModal('${book.id}')">Buy Playbook</button>`;

    return `
    <div class="book-card" data-id="${book.id}" onclick="openBookDetailsModal('${book.id}')" style="cursor:pointer;">
      ${badgeHtml}
      <div class="book-card__image-wrap">
        <img src="${book.cover}" alt="${escapeHtml(book.title)}" class="book-card__image" ${loadingAttr} decoding="async">
        <div class="book-card__preview-overlay">
          <div class="book-card__preview-pill"><i class="bi bi-eye-fill"></i> Read Playbook Details</div>
          <span style="font-size:0.75rem; color:#cbd5e1; margin-top:4px;">Tap to preview pain points & takeaways</span>
        </div>
      </div>
      <div class="book-card__content">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
          <span class="book-card__category">${escapeHtml(book.category)}</span>
          <span class="book-card__rating"><i class="bi bi-star-fill" style="color:var(--gold-bright); font-size:0.75rem;"></i> ${book.rating}</span>
        </div>
        <h3 class="book-card__title">${escapeHtml(book.title)}</h3>
        <p class="book-card__desc">${escapeHtml(book.description)}</p>
        <div class="book-card__details-action" onclick="event.stopPropagation(); openBookDetailsModal('${book.id}')">
          <i class="bi bi-info-circle-fill"></i> Read Details & Takeaways &rarr;
        </div>
        <div class="book-card__footer">
          <div class="book-card__price">
            <span class="book-card__currency"><span class="naira">₦</span></span>5,000
          </div>
          ${buttonHtml}
        </div>
      </div>
    </div>
  `;
  }).join('');
}

// ── BOOK DETAILS MODAL LOGIC ──
function openBookDetailsModal(bookId) {
  const book = BOOKS.find(b => b.id === bookId);
  if (!book) return;

  document.getElementById('details-book-cover').src = book.cover;
  document.getElementById('details-book-title').textContent = book.title;
  document.getElementById('details-book-category').textContent = book.category;
  document.getElementById('details-book-rating').textContent = book.rating;
  document.getElementById('details-book-reviews').textContent = `(${book.reviews || 200}+ verified readers)`;

  // Render Pain Points
  const painEl = document.getElementById('details-pain-points');
  if (painEl && book.painPoints) {
    painEl.innerHTML = book.painPoints.map(p => `<li>${escapeHtml(p)}</li>`).join('');
  } else if (painEl) {
    painEl.innerHTML = `<li>Solving key execution bottlenecks in ${escapeHtml(book.category)}</li>`;
  }

  // Render Solution Overview
  const solEl = document.getElementById('details-solution-overview');
  if (solEl) {
    solEl.textContent = book.solutionOverview || book.description;
  }

  // Render Takeaway Bullets
  const takeEl = document.getElementById('details-takeaways');
  if (takeEl && book.bullets) {
    takeEl.innerHTML = book.bullets.map(b => `
      <li style="display:flex; align-items:flex-start; gap:10px; font-size:0.88rem; color:#e2e8f0;">
        <i class="bi bi-check-circle-fill" style="color:#22c55e; flex-shrink:0; font-size:1.05rem; margin-top:2px;"></i>
        <span>${escapeHtml(b)}</span>
      </li>
    `).join('');
  }

  // Render Who Should Read
  const whoEl = document.getElementById('details-who-should-read');
  if (whoEl) {
    whoEl.textContent = book.whoShouldReadThis || `Ambitious performers and leaders in ${escapeHtml(book.category)}.`;
  }

  // Wire up Buy Button
  const buyBtn = document.getElementById('details-buy-btn');
  if (buyBtn) {
    buyBtn.onclick = () => {
      closeBookDetailsModal();
      openPreorderModal(book.id);
    };
  }

  document.getElementById('book-details-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeBookDetailsModal() {
  document.getElementById('book-details-modal').classList.remove('open');
  document.body.style.overflow = '';
}

function updateBundlePreviews() {
  const b1Id = document.getElementById('bundle-book-1')?.value;
  const b2Id = document.getElementById('bundle-book-2')?.value;
  const b3Id = document.getElementById('bundle-book-3')?.value;

  const b1 = BOOKS.find(b => b.id === b1Id);
  const b2 = BOOKS.find(b => b.id === b2Id);
  const b3 = BOOKS.find(b => b.id === b3Id);

  const t1 = document.getElementById('bundle-thumb-1');
  const t2 = document.getElementById('bundle-thumb-2');
  const t3 = document.getElementById('bundle-thumb-3');

  if (t1 && b1) t1.src = b1.cover;
  if (t2 && b2) t2.src = b2.cover;
  if (t3 && b3) t3.src = b3.cover;
}

function openPreorderModal(bookId) {
  const bundleContainer = document.getElementById('bundle-selector-container');
  const modalCover = document.getElementById('modal-book-cover');

  if (bookId === 'bundle_3') {
    selectedBook = {
      id: 'bundle_3',
      title: '3-Book Masterclass Bundle (Pick Any 3)',
      cover: '/assets/covers/how-to-close-high-paying-clients-in-the-dms.webp',
      description: 'Choose your 3 masterclasses below to get instant access for just ₦ 12,000 (Save ₦ 3,000 / 20% OFF).',
      amount: 12000,
      bullets: [
        "Pick any 3 masterclasses from the catalog",
        "Save ₦ 3,000 instantly vs single purchase",
        "Instant delivery & lifetime updates"
      ]
    };

    if (bundleContainer) bundleContainer.style.display = 'block';
    if (modalCover) modalCover.style.display = 'none';

    // Populate 3 dropdowns
    const optionsHtml = BOOKS.map(b => `<option value="${b.id}">${escapeHtml(b.title)}</option>`).join('');
    const s1 = document.getElementById('bundle-book-1');
    const s2 = document.getElementById('bundle-book-2');
    const s3 = document.getElementById('bundle-book-3');

    if (s1 && s2 && s3) {
      s1.innerHTML = optionsHtml;
      s2.innerHTML = optionsHtml;
      s3.innerHTML = optionsHtml;

      s1.value = 'how-to-close-high-paying-clients-in-the-dms';
      s2.value = 'how-to-build-a-high-converting-whatsapp';
      s3.value = 'naira-ads';

      updateBundlePreviews();
    }
  } else {
    const book = BOOKS.find(b => b.id === bookId);
    if (!book) return;
    selectedBook = { ...book, amount: 5000 };

    if (bundleContainer) bundleContainer.style.display = 'none';
    if (modalCover) {
      modalCover.src = book.cover;
      modalCover.style.display = 'block';
    }
  }

  document.getElementById('modal-book-title').textContent = selectedBook.title;
  document.getElementById('modal-book-desc').innerHTML = `${escapeHtml(selectedBook.description)} <div style="margin-top:8px; padding:6px 10px; background:rgba(212,175,55,0.1); border:1px solid var(--gold); border-radius:6px; color:var(--gold-bright); font-size:0.78rem; font-weight:700;"><i class="bi bi-lightning-charge-fill"></i> Delivery: Instant Access (Read On Screen + Email Delivery)</div>`;
  document.getElementById('modal-book-price-display').innerHTML = `<span class="naira">₦</span> ${(selectedBook.amount || 5000).toLocaleString()}`;
  document.getElementById('submit-preorder-btn').innerHTML = `Buy Now — <span class="naira">₦</span> ${(selectedBook.amount || 5000).toLocaleString()}`;

  const bulletsContainer = document.getElementById('modal-book-bullets');
  if (bulletsContainer && selectedBook.bullets) {
    bulletsContainer.innerHTML = selectedBook.bullets.map(b => `<li><i class="bi bi-check2-circle" style="color:var(--gold-bright);"></i> ${escapeHtml(b)}</li>`).join('');
    bulletsContainer.style.display = 'block';
  } else if (bulletsContainer) {
    bulletsContainer.style.display = 'none';
  }

  document.getElementById('preorder-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closePreorderModal() {
  document.getElementById('preorder-modal').classList.remove('open');
  document.body.style.overflow = '';
  selectedBook = null;
}

// Handle Form Submission
async function handlePreorderSubmit(e) {
  e.preventDefault();
  if (!selectedBook) return;

  const name = document.getElementById('customer-name').value.trim();
  const email = document.getElementById('customer-email').value.trim();
  const pmRadio = document.querySelector('input[name="payment_method"]:checked');
  const paymentMethod = pmRadio ? pmRadio.value : 'pay_with_bank';
  const btn = document.getElementById('submit-preorder-btn');
  const errorEl = document.getElementById('preorder-error');

  errorEl.style.display = 'none';
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';

  try {
    let bookTitleToSubmit = selectedBook.title;
    let bookIdToSubmit = selectedBook.id;

    if (selectedBook.id === 'bundle_3') {
      const b1Id = document.getElementById('bundle-book-1')?.value;
      const b2Id = document.getElementById('bundle-book-2')?.value;
      const b3Id = document.getElementById('bundle-book-3')?.value;

      const b1 = BOOKS.find(b => b.id === b1Id);
      const b2 = BOOKS.find(b => b.id === b2Id);
      const b3 = BOOKS.find(b => b.id === b3Id);

      const titleList = [b1?.title, b2?.title, b3?.title].filter(Boolean).join(' + ');
      bookTitleToSubmit = `3-Book Bundle: ${titleList}`;
      bookIdToSubmit = `bundle_3_${b1Id || 'b1'}_${b2Id || 'b2'}_${b3Id || 'b3'}`;

      // Save pending bundle IDs to local storage so they are automatically added to library on success
      try {
        localStorage.setItem('scale_pending_bundle_ids', JSON.stringify([b1Id, b2Id, b3Id]));
      } catch(err){}
    }

    const referralCode = localStorage.getItem('ac_referral_code');
    const amountToCharge = selectedBook.amount || 5000;
    const res = await fetch(`${API_BASE}/payments/preorder/initialize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        email,
        book_id: bookIdToSubmit,
        book_title: bookTitleToSubmit,
        amount: amountToCharge,
        payment_method: paymentMethod,
        referral_code: referralCode || null,
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Initialization failed');

    if (data.action === 'redirect' && data.redirect_url) {
      window.location.href = data.redirect_url;
      return;
    }
    throw new Error('Could not initiate checkout redirect.');
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.style.display = 'block';
    btn.disabled = false;
    btn.innerHTML = `Buy Now — <span class="naira">₦</span> ${(selectedBook.amount || 5000).toLocaleString()}`;
  }
}

// Check Success & Refund Request Modals
function checkSuccessState() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('preorder_success') === '1') {
    const ref = params.get('ref') || '';
    const title = params.get('title') || 'Your Masterclass';
    const bookId = params.get('book_id');
    if (bookId) addOwnedBook(bookId);

    // Process pending bundle IDs if present
    try {
      const pendingRaw = localStorage.getItem('scale_pending_bundle_ids');
      if (pendingRaw) {
        const pIds = JSON.parse(pendingRaw);
        pIds.forEach(id => addOwnedBook(id));
        localStorage.removeItem('scale_pending_bundle_ids');
      }
    } catch(e){}

    showSuccessModal(ref, title);
  }
}

function showSuccessModal(ref, title) {
  document.getElementById('success-ref-display').textContent = ref;
  document.getElementById('success-title-display').textContent = title;
  document.getElementById('success-modal').classList.add('open');
}

function closeSuccessModal() {
  document.getElementById('success-modal').classList.remove('open');
  window.history.replaceState({}, document.title, window.location.pathname);
}

function openRefundModal() {
  document.getElementById('refund-modal').classList.add('open');
}

function closeRefundModal() {
  document.getElementById('refund-modal').classList.remove('open');
}

async function handleRefundSubmit(e) {
  e.preventDefault();
  const ref = document.getElementById('refund-ref').value.trim();
  const email = document.getElementById('refund-email').value.trim();
  const reason = document.getElementById('refund-reason').value.trim();
  const btn = document.getElementById('submit-refund-btn');
  const statusEl = document.getElementById('refund-status-msg');

  btn.disabled = true;
  btn.textContent = 'Submitting...';

  try {
    const res = await fetch(`${API_BASE}/preorders/request-refund`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reference: ref, email, reason }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Refund submission failed');

    statusEl.className = 'status-msg status-msg--success';
    statusEl.textContent = data.message;
    statusEl.style.display = 'block';
    setTimeout(closeRefundModal, 4000);
  } catch (err) {
    statusEl.className = 'status-msg status-msg--error';
    statusEl.textContent = err.message;
    statusEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Submit Refund Request';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// ── LEAD MAGNET & VIRAL REFERRAL LOGIC ──
function openLeadMagnetModal() {
  const modal = document.getElementById('lead-magnet-modal');
  if (modal) {
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
}

function closeLeadMagnetModal() {
  const modal = document.getElementById('lead-magnet-modal');
  if (modal) {
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }
}

function closeLeadMagnetSuccessModal() {
  const modal = document.getElementById('lead-magnet-success-modal');
  if (modal) {
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }
}

async function handleLeadMagnetSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('lm-name').value.trim();
  const email = document.getElementById('lm-email').value.trim();
  const category = document.getElementById('lm-category').value;
  const btn = document.getElementById('submit-lm-btn');
  const statusEl = document.getElementById('lm-status-msg');

  statusEl.style.display = 'none';
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Dispatched...';

  try {
    const referralCode = localStorage.getItem('ac_referral_code') || null;
    const res = await fetch(`${API_BASE}/lead-magnet/opt-in`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        email,
        category,
        referral_code: referralCode
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Opt-in submission failed');

    closeLeadMagnetModal();

    // Populate success modal referral details
    const refInput = document.getElementById('subscriber-referral-link');
    const emailDisp = document.getElementById('lm-success-email');

    if (refInput && data.referral_link) {
      refInput.value = data.referral_link;
    }
    if (emailDisp) {
      emailDisp.textContent = email;
    }

    const successModal = document.getElementById('lead-magnet-success-modal');
    if (successModal) {
      successModal.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    btn.disabled = false;
    btn.innerHTML = 'Send Me The Free Cheat Sheet &rarr;';
  } catch (err) {
    statusEl.className = 'status-msg status-msg--error';
    statusEl.textContent = err.message;
    statusEl.style.display = 'block';
    btn.disabled = false;
    btn.innerHTML = 'Send Me The Free Cheat Sheet &rarr;';
  }
}

function copyReferralLink() {
  const refInput = document.getElementById('subscriber-referral-link');
  if (!refInput) return;
  refInput.select();
  navigator.clipboard.writeText(refInput.value);
  alert('Referral link copied to clipboard! Share with 2 friends to unlock free masterclasses.');
}

function shareReferralWhatsApp() {
  const refInput = document.getElementById('subscriber-referral-link');
  const link = refInput ? refInput.value : window.location.href;
  const text = encodeURIComponent(`Hey! I just got this free cheat sheet: "The 15-Minute DM Objection Matrix (5 Copy-Paste Closing Scripts)". Get your free copy here: ${link}`);
  window.open(`https://api.whatsapp.com/send?text=${text}`, '_blank');
}

function shareReferralTwitter() {
  const refInput = document.getElementById('subscriber-referral-link');
  const link = refInput ? refInput.value : window.location.href;
  const text = encodeURIComponent(`Just claimed "The 15-Minute DM Objection Matrix" cheat sheet. Stop getting left on read when sending prices: ${link}`);
  window.open(`https://twitter.com/intent/tweet?text=${text}`, '_blank');
}
