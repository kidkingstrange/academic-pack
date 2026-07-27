/**
 * Multi-Book Homepage Logic — Catalog & Direct Checkout Management
 */
const API_BASE = '/api';

const BOOKS = [
  {
    id: "how-to-close-high-paying-clients-in-the-dms",
    title: "How to Close High-Paying Clients in the DMs",
    cover: "/assets/covers/how-to-close-high-paying-clients-in-the-dms.png",
    category: "Sales & Marketing",
    description: "The complete script, objection handling, and conversation framework to close high-ticket deals inside social media DMs."
  },
  {
    id: "how-to-build-a-high-converting-whatsapp",
    title: "How to Build a High-Converting WhatsApp Sales Funnel",
    cover: "/assets/covers/how-to-build-a-high-converting-whatsapp.png",
    category: "Sales & Marketing",
    description: "Turn your WhatsApp broadcast and status into an automated sales machine that converts cold leads into eager buyers."
  },
  {
    id: "how-to-sell-digital-products-globally",
    title: "How to Sell Digital Products Globally",
    cover: "/assets/covers/how-to-sell-digital-products-globally.png",
    category: "Sales & Marketing",
    description: "Frameworks for building, pricing, and distributing digital products to international buyers from Nigeria."
  },
  {
    id: "naira-ads",
    title: "Naira Ads Masterclass: Scale Your Business with Meta Ads",
    cover: "/assets/covers/naira-ads.png",
    category: "Sales & Marketing",
    description: "Run profitable Facebook and Instagram ads using Naira accounts without ban risks or payment failures."
  },
  {
    id: "how-to-land-high-paying-corporate-clients",
    title: "How to Land High-Paying Corporate Clients",
    cover: "/assets/covers/how-to-land-high-paying-corporate-clients.png",
    category: "Sales & Marketing",
    description: "Position yourself, pitch decision-makers, and win high-retainer B2B corporate contracts."
  },
  {
    id: "how-to-build-a-business-that-functions-without",
    title: "How to Build a Business That Functions Without You",
    cover: "/assets/covers/how-to-build-a-business-that-functions-without.png",
    category: "Business & Scale",
    description: "Systematize operations, delegate responsibilities, and create SOPs so your business runs smoothly when you step away."
  },
  {
    id: "how-to-fund-your-business-with-upfront",
    title: "How to Fund Your Business with Upfront Client Cash",
    cover: "/assets/covers/how-to-fund-your-business-with-upfront.png",
    category: "Business & Scale",
    description: "Bootstrapping playbook to pre-sell services and fund expansion using upfront client payments instead of debt."
  },
  {
    id: "how-to-maintain-positive-cash-flow-under",
    title: "How to Maintain Positive Cash Flow Under Pressure",
    cover: "/assets/covers/how-to-maintain-positive-cash-flow-under.png",
    category: "Business & Scale",
    description: "Cash flow management strategies for volatile markets, inflation, and unpredictable revenue cycles."
  },
  {
    id: "how-to-qualify-and-filter-out-low",
    title: "How to Qualify and Filter Out Low-Paying Clients",
    cover: "/assets/covers/how-to-qualify-and-filter-out-low.png",
    category: "Business & Scale",
    description: "Stop wasting time on budget-constrained clients and establish qualifying filters that attract premium buyers."
  },
  {
    id: "how-to-stop-worrying-about-money",
    title: "How to Stop Worrying About Money & Build Security",
    cover: "/assets/covers/how-to-stop-worrying-about-money.png",
    category: "Finance & Wealth",
    description: "Psychological principles and tactical money management systems to eliminate financial anxiety."
  },
  {
    id: "how-to-transition-from-a-side-hustle-to",
    title: "How to Transition from a Side Hustle to Full-Time Enterprise",
    cover: "/assets/covers/how-to-transition-from-a-side-hustle-to.png",
    category: "Business & Scale",
    description: "Risk-calculated roadmap for quitting your 9-to-5 safely and scaling your business full-time."
  },
  {
    id: "how-to-ask-for-the-promotion-and",
    title: "How to Ask for the Promotion and Get It",
    cover: "/assets/covers/how-to-ask-for-the-promotion-and.png",
    category: "Career Acceleration",
    description: "Proven corporate negotiation scripts and performance proof frameworks to secure salary increases and titles."
  },
  {
    id: "how-to-get-seen-by-the-people-who-actually-decide",
    title: "How to Get Seen by the People Who Actually Decide Your Promotion",
    cover: "/assets/covers/how-to-get-seen-by-the-people-who-actually-decide.png",
    category: "Career Acceleration",
    description: "Strategic executive visibility tactics to make your work noticeable to senior leadership and key stakeholders."
  },
  {
    id: "how-to-expand-your-role-before-anyone",
    title: "How to Expand Your Role Before Anyone Asks",
    cover: "/assets/covers/how-to-expand-your-role-before-anyone.png",
    category: "Career Acceleration",
    description: "Proactive career ownership techniques to carve out high-impact responsibilities and fast-track advancement."
  },
  {
    id: "how-to-master-your-role-so-well",
    title: "How to Master Your Role So Well You Become Irreplaceable",
    cover: "/assets/covers/how-to-master-your-role-so-well.png",
    category: "Career Acceleration",
    description: "Operational excellence and skill stack building to become an essential key player in any organization."
  },
  {
    id: "how-to-navigate-the-unspoken-rules-and",
    title: "How to Navigate the Unspoken Rules of Workplace Politics",
    cover: "/assets/covers/how-to-navigate-the-unspoken-rules-and.png",
    category: "Career Acceleration",
    description: "Corporate dynamics, alliance building, and self-preservation in competitive office environments."
  },
  {
    id: "how-to-think-like-a-leader-before-you-have",
    title: "How to Think Like a Leader Before You Have the Title",
    cover: "/assets/covers/how-to-think-like-a-leader-before-you-have.png",
    category: "Career Acceleration",
    description: "Strategic leadership mindset, decision-making frameworks, and influence building for aspiring executives."
  },
  {
    id: "how-to-turn-your-boss-into-your-biggest",
    title: "How to Turn Your Boss Into Your Biggest Career Advocate",
    cover: "/assets/covers/how-to-turn-your-boss-into-your-biggest.png",
    category: "Career Acceleration",
    description: "Managing up, aligning goals, and turning your direct manager into your active sponsor."
  },
  {
    id: "how-to-heal-your-body-from-stress",
    title: "How to Heal Your Body from Chronic Stress & Burnout",
    cover: "/assets/covers/how-to-heal-your-body-from-stress.png",
    category: "Mindset & Health",
    description: "Somatic recovery techniques and energy management for high achievers facing burnout."
  },
  {
    id: "how-to-overcome-decision-paralysis",
    title: "How to Overcome Decision Paralysis and Take Action",
    cover: "/assets/covers/how-to-overcome-decision-paralysis.png",
    category: "Mindset & Health",
    description: "Frameworks to eliminate overthinking, reduce analysis paralysis, and execute with confidence."
  },
  {
    id: "how-to-set-boundaries-with-family",
    title: "How to Set Boundaries with Family, Money, and Time",
    cover: "/assets/covers/how-to-set-boundaries-with-family.png",
    category: "Mindset & Health",
    description: "Assertive communication and emotional boundary setting to protect your focus, energy, and finances."
  },
  {
    id: "how-to-stay-calm-in-chaos",
    title: "How to Stay Calm in Chaos and High-Pressure Environments",
    cover: "/assets/covers/how-to-stay-calm-in-chaos.png",
    category: "Mindset & Health",
    description: "Stoic mental models and emotional regulation techniques for high-stakes pressure situations."
  },
  {
    id: "how-to-stop-learning-and-start-executing",
    title: "How to Stop Learning and Start Executing Today",
    cover: "/assets/covers/how-to-stop-learning-and-start-executing.png",
    category: "Mindset & Health",
    description: "Break the cycle of endless tutorials and course hoarding — switch to active output and real-world results."
  },
  {
    id: "book1",
    title: "Academic Comeback Package",
    cover: "/assets/covers/book1.png",
    category: "Education & Mastery",
    description: "The signature system for students who study hard but fail to get expected grades. Learn effective learning systems."
  },
  {
    id: "book2",
    title: "Scale & Execution Blueprint",
    cover: "/assets/covers/book2.png",
    category: "Business & Scale",
    description: "High-level execution architecture for business owners, creators, and professionals scaling operations."
  },
  {
    id: "book3",
    title: "High-Income Skill Acceleration",
    cover: "/assets/covers/book3.png",
    category: "Career Acceleration",
    description: "Identify, master, and monetize high-value market skills in 90 days or less."
  },
  {
    id: "book4",
    title: "Corporate Career Velocity",
    cover: "/assets/covers/book4.png",
    category: "Career Acceleration",
    description: "Accelerated career advancement and income multiplication playbook for corporate professionals."
  },
  {
    id: "book5",
    title: "Financial Mastery & Cash Flow",
    cover: "/assets/covers/book5.png",
    category: "Finance & Wealth",
    description: "Personal and business cash flow management, asset allocation, and wealth preservation."
  },
  {
    id: "book6",
    title: "Mental Toughness & Peak Performance",
    cover: "/assets/covers/book6.png",
    category: "Mindset & Health",
    description: "Develop unshakeable discipline, focus stamina, and high-performance habits under pressure."
  },
  {
    id: "book7",
    title: "Digital Product & DM Closing Blueprint",
    cover: "/assets/covers/book7.png",
    category: "Sales & Marketing",
    description: "Complete guide to creating, marketing, and selling digital assets directly through conversational sales."
  }
];

let selectedBook = null;

document.addEventListener('DOMContentLoaded', () => {
  // Capture affiliate code from URL if present
  const urlParams = new URLSearchParams(window.location.search);
  const refCode = urlParams.get('ref');
  if (refCode) {
    try { localStorage.setItem('ac_referral_code', refCode.trim().toUpperCase()); } catch(e){}
  }

  renderBooks();
  checkSuccessState();
});

function renderBooks() {
  const grid = document.getElementById('books-grid');
  if (!grid) return;

  grid.innerHTML = BOOKS.map(book => `
    <div class="book-card" data-id="${book.id}">
      <div class="book-card__badge">Available Now</div>
      <div class="book-card__image-wrap">
        <img src="${book.cover}" alt="${escapeHtml(book.title)}" class="book-card__image" loading="lazy">
      </div>
      <div class="book-card__content">
        <span class="book-card__category">${escapeHtml(book.category)}</span>
        <h3 class="book-card__title">${escapeHtml(book.title)}</h3>
        <p class="book-card__desc">${escapeHtml(book.description)}</p>
        <div class="book-card__footer">
          <div class="book-card__price">
            <span class="book-card__currency">₦</span>5,000
          </div>
          <button class="btn btn--gold book-card__btn" onclick="openPreorderModal('${book.id}')">
            Buy Now
          </button>
        </div>
      </div>
    </div>
  `).join('');
}

function openPreorderModal(bookId) {
  const book = BOOKS.find(b => b.id === bookId);
  if (!book) return;
  selectedBook = book;

  document.getElementById('modal-book-title').textContent = book.title;
  document.getElementById('modal-book-cover').src = book.cover;
  document.getElementById('modal-book-desc').textContent = book.description;
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
    const referralCode = localStorage.getItem('ac_referral_code');
    const res = await fetch(`${API_BASE}/payments/preorder/initialize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        email,
        book_id: selectedBook.id,
        book_title: selectedBook.title,
        amount: 5000,
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
    btn.innerHTML = 'Buy Now — ₦5,000';
  }
}

// Check Success & Refund Request Modals
function checkSuccessState() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('preorder_success') === '1') {
    const ref = params.get('ref') || '';
    const title = params.get('title') || 'Your Book';
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
