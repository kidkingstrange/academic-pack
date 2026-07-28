/**
 * Multi-Book Homepage Logic — Catalog, Search, Filtering & Retention Management
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
    bullets: [
      "Copy-paste DM opening scripts that get 80%+ response rates",
      "Overcoming the 'It's too expensive' objection effortlessly",
      "Transitioning from casual conversation to a 5-figure retainer"
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
    bullets: [
      "Broadcast sequence structure for instant daily sales",
      "Status copywriting formula that builds buying intent",
      "Automating contact saving & lead capture on WhatsApp"
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
    bullets: [
      "Setting up multi-currency international Paystack checkout",
      "Targeting buyers in US, UK, Canada & Europe with high purchasing power",
      "Pricing digital products in USD and EUR for maximum margin"
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
    bullets: [
      "Setting up ban-proof Naira ad accounts on Meta",
      "High-ROAS creative templates for local and global audiences",
      "Scaling daily ad spend while staying profitable"
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
    bullets: [
      "Finding and reaching executive decision-makers directly",
      "Writing winning B2B proposal decks that close fast",
      "Structuring annual retainer agreements with 7-figure scope"
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
    bullets: [
      "Creating step-by-step SOPs your team actually follows",
      "Hiring & training reliable operations managers",
      "Removing yourself from daily execution bottleneck"
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
    bullets: [
      "Pre-selling new services before building them",
      "Securing 50%–100% upfront deposits on custom projects",
      "Cash flow preservation systems for fast-growing companies"
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
    bullets: [
      "Building a 6-month operational cash reserve buffer",
      "Hedging against FX devaluation and rising expenses",
      "Managing receivables to eliminate late customer payments"
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
    bullets: [
      "Red-flag client identification in the first 5 minutes",
      "Application forms that filter out price shoppers",
      "Polite scripts to decline bad-fit clients gracefully"
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
    bullets: [
      "Automating personal savings and emergency funds",
      "Decoupling stress from monthly income fluctuations",
      "Building predictable long-term financial security"
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
    bullets: [
      "Calculating your minimum safe exit revenue baseline",
      "Managing job performance while building your business after hours",
      "First 90 days full-time execution strategy"
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
    bullets: [
      "Building an undeniable 'Brag Sheet' of quantitative business wins",
      "Timing your raise request for maximum success probability",
      "Handling salary pushback and securing title progression"
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
    bullets: [
      "Getting assigned to high-visibility strategic projects",
      "Presenting effectively to C-suite decision-makers",
      "Building internal executive sponsorships across departments"
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
    bullets: [
      "Identifying unaddressed company problems and solving them first",
      "Creating new role definitions tailored to your strengths",
      "Fast-tracking leadership recognition without waiting for permission"
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
    bullets: [
      "Developing niche domain expertise no one else possesses",
      "Optimized speed and quality output frameworks",
      "Protecting your position against downsizing and restructuring"
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
    bullets: [
      "Mapping power structures and hidden decision alliances",
      "Protecting your credit and ideas from credit stealers",
      "Ethical office diplomacy that accelerates career growth"
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
    bullets: [
      "Thinking in company ROI rather than task completion",
      "Leading peers and cross-functional teams with authority",
      "Executive decision-making under uncertainty"
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
    bullets: [
      "Aligning your daily work with your manager's top KPIs",
      "Conducting high-impact 1-on-1 career alignment meetings",
      "Turning difficult managers into helpful career sponsors"
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
    bullets: [
      "Lowering cortisol and nervous system over-arousal",
      "Restoring deep sleep and physical stamina",
      "Building high-output routines without exhausting your body"
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
    bullets: [
      "The 5-minute bias-to-action rule for complex decisions",
      "Eliminating fear of making wrong choices",
      "Daily execution systems that replace motivation dependency"
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
    bullets: [
      "Saying NO to financial demands guilt-free",
      "Protecting deep-work focus hours from family interruptions",
      "Scripts for handling difficult personal conversations"
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
    bullets: [
      "Instant physiological calm techniques under sudden crisis",
      "Maintaining objective clarity when stakes are extremely high",
      "Developing an unshakeable mental armor"
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
    bullets: [
      "Breaking tutorial hell and passive learning addiction",
      "Converting knowledge into immediate cash flow output",
      "The 80/20 execution ratio for rapid skill mastery"
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
    bullets: [
      "Time allocation framework for student founders",
      "Prioritizing coursework while running a business",
      "Managing stress and maintaining top academic performance"
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
    bullets: [
      "Active recall & spaced repetition study schedule",
      "Deconstructing exam questions for maximum marks",
      "Eliminating exam anxiety & last-minute cramming"
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
    bullets: [
      "Identifying high-yield exam topics & past question trends",
      "Feynman technique for rapid concept comprehension",
      "Studying less hours while achieving higher retention"
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
    bullets: [
      "Deliberate practice protocol for difficult subjects",
      "Building 4-hour deep focus stamina",
      "Overcoming frustration & cognitive fatigue"
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
    bullets: [
      "Daily habit tracking grid for 30-day exam prep",
      "Measuring daily topic completion & review milestones",
      "Building unshakeable consistency and study momentum"
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
    bullets: [
      "Digital environment distraction elimination framework",
      "Structured Pomodoro & deep work sprint blocks",
      "Restoring mental clarity and focus control"
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
    bullets: [
      "48-hour pre-exam emergency review protocol",
      "Pacing strategies inside the examination hall",
      "Handling unexpected questions under severe time pressure"
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
      : `<div class="book-card__badge">Instant PDF</div>`;

    const buttonHtml = isOwned
      ? `<button class="btn btn--green book-card__btn" onclick="location.href='/library'">Read Now</button>`
      : `<button class="btn btn--gold book-card__btn" onclick="openPreorderModal('${book.id}')">Buy Now</button>`;

    return `
    <div class="book-card" data-id="${book.id}">
      ${badgeHtml}
      <div class="book-card__image-wrap">
        <img src="${book.cover}" alt="${escapeHtml(book.title)}" class="book-card__image" ${loadingAttr} decoding="async">
      </div>
      <div class="book-card__content">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
          <span class="book-card__category">${escapeHtml(book.category)}</span>
          <span style="font-size:0.68rem; color:var(--text-muted); display:flex; align-items:center; gap:3px;"><i class="bi bi-file-earmark-pdf-fill" style="color:var(--gold);"></i> PDF</span>
        </div>
        <h3 class="book-card__title">${escapeHtml(book.title)}</h3>
        <p class="book-card__desc">${escapeHtml(book.description)}</p>
        <div class="book-card__footer">
          <div class="book-card__price">
            <span class="book-card__currency"><span class="naira">₦</span> </span>5,000
          </div>
          ${buttonHtml}
        </div>
      </div>
    </div>
  `;
  }).join('');
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
  document.getElementById('modal-book-desc').innerHTML = `${escapeHtml(selectedBook.description)} <div style="margin-top:8px; padding:6px 10px; background:rgba(212,175,55,0.1); border:1px solid var(--gold); border-radius:6px; color:var(--gold-bright); font-size:0.78rem; font-weight:700;"><i class="bi bi-lightning-charge-fill"></i> Format: Instant PDF Download (On-screen + Email Delivery)</div>`;
  document.getElementById('modal-book-price-display').innerHTML = `<span class="naira">₦</span> ${(selectedBook.amount || 5000).toLocaleString()}`;
  document.getElementById('submit-preorder-btn').innerHTML = `Get Instant PDF — <span class="naira">₦</span> ${(selectedBook.amount || 5000).toLocaleString()}`;

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
