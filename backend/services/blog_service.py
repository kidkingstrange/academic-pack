"""
Blog Service: Markdown/Frontmatter parser, HTML generator, JSON-LD Schema builder,
static site compiler, and sitemap generator for the Academic Comeback Blog.
"""

import os
import re
import json
import html
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Root directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONTENT_DIR = BASE_DIR / "content"
ARTICLES_DIR = CONTENT_DIR / "articles"
CATEGORIES_FILE = CONTENT_DIR / "categories.json"
FRONTEND_DIR = BASE_DIR / "frontend"
BLOG_OUTPUT_DIR = FRONTEND_DIR / "blog"
SITEMAP_FILE = FRONTEND_DIR / "sitemap.xml"

SITE_URL = "https://academic-pack.onrender.com"

# Ensure directories exist
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
BLOG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_categories() -> List[Dict[str, Any]]:
    """Load categories definition from content/categories.json."""
    if CATEGORIES_FILE.exists():
        try:
            with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [
        {
            "slug": "academics",
            "name": "Academics & Study Systems",
            "short_desc": "Tactical study systems, active recall protocols, and CGPA comeback frameworks.",
            "intro": "Proven study frameworks, active recall, exam hall mastery, and CGPA recovery strategies specifically designed for Nigerian university students navigating intense semester workloads.",
            "icon": "bi-mortarboard-fill",
            "color": "#d4a63a"
        },
        {
            "slug": "hostel-and-accommodation",
            "name": "Hostel & Accommodation Life",
            "short_desc": "Campus hostels, off-campus lodges, and roommate harmony in Nigerian universities.",
            "intro": "Essential survival guides for campus hostels, off-campus lodges, power outages (NEPA/PHCN), noise management, and roommate dynamics across Nigerian universities.",
            "icon": "bi-house-door-fill",
            "color": "#38bdf8"
        },
        {
            "slug": "mental-health",
            "name": "Student Mental Health & Well-being",
            "short_desc": "Actionable mental health support, anxiety relief, and burnout prevention.",
            "intro": "Practical mental health coping strategies for exam anxiety, academic pressure, burnout, depression, and imposter syndrome in demanding Nigerian higher institutions.",
            "icon": "bi-heart-pulse-fill",
            "color": "#ec4899"
        },
        {
            "slug": "finances",
            "name": "Student Finances & Budgeting",
            "short_desc": "Smart budgeting frameworks, student savings strategies, and meal planning hacks.",
            "intro": "Smart budgeting, meal planning, student savings tips, emergency funds, and managing allowance in the face of inflation across Nigerian campuses.",
            "icon": "bi-wallet2",
            "color": "#22c55e"
        },
        {
            "slug": "balancing-work-and-school",
            "name": "Balancing Work & School",
            "short_desc": "Operating frameworks for student entrepreneurs, freelancers, and tech workers.",
            "intro": "Tactical operating systems for student entrepreneurs, freelancers, remote tech workers, and creatives juggling tight academic schedules without sacrificing their grades.",
            "icon": "bi-briefcase-fill",
            "color": "#a855f7"
        }
    ]


def get_category_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    for cat in get_categories():
        if cat["slug"] == slug:
            return cat
    return None


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    Parse YAML-style frontmatter from markdown text without requiring external pyyaml.
    Handles strings, lists, integers, and nested FAQ arrays.
    """
    metadata: Dict[str, Any] = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_meta = parts[1]
            body = parts[2].strip()

            lines = raw_meta.strip().split("\n")
            current_key = None
            current_list: Optional[List[Any]] = None
            current_dict: Optional[Dict[str, str]] = None

            for line in lines:
                raw_line = line
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Check for list item under current_key (e.g. faq item)
                if line.startswith("- "):
                    item_text = line[2:].strip()
                    # Check if this is a dict inside a list (like `- question: "..."`)
                    if ":" in item_text and not (item_text.startswith('"') and item_text.endswith('"')):
                        sub_k, sub_v = item_text.split(":", 1)
                        sub_k = sub_k.strip()
                        sub_v = sub_v.strip().strip('"').strip("'")
                        current_dict = {sub_k: sub_v}
                        if current_list is not None:
                            current_list.append(current_dict)
                    else:
                        val = item_text.strip('"').strip("'")
                        if current_list is not None:
                            current_list.append(val)
                    continue

                # Check for indented dict key under current list item
                if raw_line.startswith("    ") or raw_line.startswith("  "):
                    if current_dict is not None and ":" in line:
                        sub_k, sub_v = line.split(":", 1)
                        current_dict[sub_k.strip()] = sub_v.strip().strip('"').strip("'")
                        continue

                # Normal key: value
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip()

                    if not val:
                        # Start of list or nested object
                        current_key = key
                        current_list = []
                        metadata[key] = current_list
                        current_dict = None
                    else:
                        # Clean quotes
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        elif val.lower() == "true":
                            val = True
                        elif val.lower() == "false":
                            val = False
                        metadata[key] = val
                        current_key = None
                        current_list = None
                        current_dict = None

    return metadata, body


def resolve_internal_link_placeholders(md_text: str) -> str:
    """
    Sanitize and transform any developer placeholders matching:
    [INTERNAL LINK: <anchor text> -> article #<num> from the master plan]
    into authentic, clickable internal markdown hyperlinks.
    """
    map_file = CONTENT_DIR / "article_link_map.json"
    link_map = {}
    if map_file.exists():
        try:
            with open(map_file, "r", encoding="utf-8") as f:
                link_map = json.load(f)
        except Exception:
            pass

    pattern = re.compile(r"\[INTERNAL LINK:\s*(.*?)\s*->\s*article\s*#(\d+)[^\]]*\]", re.IGNORECASE)

    def _replace(match):
        anchor = match.group(1).strip()
        num_str = match.group(2).strip()
        item = link_map.get(num_str)
        if not item:
            return anchor
        cat = item.get("category", "academics")
        slug = item.get("slug")
        if item.get("published") and slug:
            return f"[{anchor}](/blog/{cat}/{slug}/)"
        return f"[{anchor}](/blog/{cat}/)"

    return pattern.sub(_replace, md_text)


def markdown_to_html(md_text: str) -> str:
    """
    Convert Markdown to clean, semantic HTML.
    Uses Python's `markdown` library with standard extensions if installed,
    with an internal fallback parser if unavailable.
    """
    md_text = resolve_internal_link_placeholders(md_text)
    try:
        import markdown
        html = markdown.markdown(
            md_text,
            extensions=[
                "extra",
                "tables",
                "toc",
                "nl2br",
                "sane_lists"
            ]
        )
        # Format interactive checklist items
        html = re.sub(r'<li>\s*\[\s*\]\s*', '<li class="task-list-item"><span class="task-checkbox"></span>', html)
        html = re.sub(r'<li>\s*\[[xX]\]\s*', '<li class="task-list-item is-checked"><span class="task-checkbox is-checked"></span>', html)
        return html
    except Exception:
        pass

    # Resilient fallback parser
    lines = md_text.split("\n")
    html_lines = []
    in_list = False
    list_type = "ul"
    in_blockquote = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append(f"</{list_type}>")
                in_list = False
            if in_blockquote:
                html_lines.append("</blockquote>")
                in_blockquote = False
            continue

        # Headings
        if stripped.startswith("### "):
            heading_text = stripped[4:]
            slug_id = re.sub(r"[^a-z0-9]+", "-", heading_text.lower()).strip("-")
            html_lines.append(f'<h3 id="{slug_id}">{heading_text}</h3>')
            continue
        elif stripped.startswith("## "):
            heading_text = stripped[3:]
            slug_id = re.sub(r"[^a-z0-9]+", "-", heading_text.lower()).strip("-")
            html_lines.append(f'<h2 id="{slug_id}">{heading_text}</h2>')
            continue
        elif stripped.startswith("# "):
            heading_text = stripped[2:]
            slug_id = re.sub(r"[^a-z0-9]+", "-", heading_text.lower()).strip("-")
            html_lines.append(f'<h1 id="{slug_id}">{heading_text}</h1>')
            continue

        # Horizontal Rule
        if stripped in ["---", "***", "___"]:
            html_lines.append("<hr>")
            continue

        # Blockquote
        if stripped.startswith("> "):
            if not in_blockquote:
                html_lines.append("<blockquote>")
                in_blockquote = True
            content = stripped[2:]
            html_lines.append(f"<p>{content}</p>")
            continue

        # Unordered list
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
                list_type = "ul"
            item = stripped[2:]
            html_lines.append(f"<li>{item}</li>")
            continue

        # Numbered list
        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            if not in_list:
                html_lines.append("<ol>")
                in_list = True
                list_type = "ol"
            item = m.group(1)
            html_lines.append(f"<li>{item}</li>")
            continue

        # Standard paragraph or custom HTML blocks
        if stripped.startswith("<") and stripped.endswith(">"):
            html_lines.append(stripped)
        else:
            # Inline formatting
            formatted = stripped
            # Bold & italic
            formatted = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", formatted)
            formatted = re.sub(r"\*(.*?)\*", r"<em>\1</em>", formatted)
            # Links
            formatted = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', formatted)
            # Images
            formatted = re.sub(
                r"!\[(.*?)\]\((.*?)\)",
                r'<img src="\2" alt="\1" loading="lazy" decoding="async">',
                formatted
            )
            html_lines.append(f"<p>{formatted}</p>")

    if in_list:
        html_lines.append(f"</{list_type}>")
    if in_blockquote:
        html_lines.append("</blockquote>")

    raw_result = "\n".join(html_lines)
    raw_result = re.sub(r'<li>\s*\[\s*\]\s*', '<li class="task-list-item"><span class="task-checkbox"></span>', raw_result)
    raw_result = re.sub(r'<li>\s*\[[xX]\]\s*', '<li class="task-list-item is-checked"><span class="task-checkbox is-checked"></span>', raw_result)
    return raw_result


def load_article_from_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Reads and parses an article file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    meta, raw_body = parse_frontmatter(content)
    slug = meta.get("slug") or file_path.stem

    # Category validation
    category_slug = meta.get("category", "academics")
    category = get_category_by_slug(category_slug) or get_categories()[0]

    # Convert markdown body to HTML
    body_html = markdown_to_html(raw_body)

    # Word count & Read time calculation
    words = len(re.findall(r"\w+", raw_body))
    read_minutes = max(1, round(words / 200))
    read_time = meta.get("read_time", f"{read_minutes} min read")

    return {
        "slug": slug,
        "title": meta.get("title", slug.replace("-", " ").title()),
        "description": meta.get("description", "A practical guide for Nigerian university students."),
        "category": category_slug,
        "category_name": category["name"],
        "category_color": category.get("color", "#b45309"),
        "category_bg": category.get("bg_color", "#fef3c7"),
        "category_border": category.get("border_color", "#fde68a"),
        "author": meta.get("author", "Itoya David"),
        "author_role": meta.get("author_role", "Academic Strategist & Founder"),
        "date_published": meta.get("date_published", datetime.now().strftime("%Y-%m-%d")),
        "date_modified": meta.get("date_modified", datetime.now().strftime("%Y-%m-%d")),
        "status": meta.get("status", "draft"),
        "featured_image": meta.get("featured_image", ""),
        "featured_image_alt": meta.get("featured_image_alt", meta.get("title", "Article image")),
        "faq": meta.get("faq", []),
        "read_time": read_time,
        "raw_markdown": raw_body,
        "body_html": body_html,
        "file_path": str(file_path)
    }


def get_all_articles(include_drafts: bool = False) -> List[Dict[str, Any]]:
    """Loads all articles from content/articles directory sorted by date desc."""
    articles = []
    if not ARTICLES_DIR.exists():
        return articles

    for file_path in ARTICLES_DIR.glob("*.md"):
        article = load_article_from_file(file_path)
        if article:
            if include_drafts or article["status"] == "published":
                articles.append(article)

    # Sort by date desc
    articles.sort(key=lambda a: a.get("date_published", ""), reverse=True)
    return articles


def get_article_by_slug(slug: str, include_drafts: bool = True) -> Optional[Dict[str, Any]]:
    """Finds an article by its slug."""
    for file_path in ARTICLES_DIR.glob("*.md"):
        article = load_article_from_file(file_path)
        if article and article["slug"] == slug:
            if include_drafts or article["status"] == "published":
                return article
    return None


def generate_json_ld(article: Dict[str, Any]) -> str:
    """Generates schema.org JSON-LD structured data (@graph with BlogPosting, BreadcrumbList, FAQPage)."""
    canonical_url = f"{SITE_URL}/blog/{article['category']}/{article['slug']}"
    category_url = f"{SITE_URL}/blog/{article['category']}/"

    # 1. Breadcrumbs
    breadcrumbs = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": f"{SITE_URL}/"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Blog",
                "item": f"{SITE_URL}/blog/"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": article["category_name"],
                "item": category_url
            },
            {
                "@type": "ListItem",
                "position": 4,
                "name": article["title"],
                "item": canonical_url
            }
        ]
    }

    # 2. BlogPosting
    full_image_url = article.get("featured_image", "")
    if not full_image_url or "bookcover.webp" in full_image_url:
        full_image_url = f"{SITE_URL}/assets/images/scale-logo-512.png"
    elif full_image_url.startswith("/"):
        full_image_url = f"{SITE_URL}{full_image_url}"

    blog_posting = {
        "@type": "BlogPosting",
        "@id": f"{canonical_url}#article",
        "isPartOf": {
            "@type": "WebSite",
            "@id": f"{SITE_URL}/#website",
            "name": "Academic Comeback",
            "url": SITE_URL
        },
        "headline": article["title"],
        "description": article["description"],
        "image": full_image_url,
        "datePublished": f"{article['date_published']}T08:00:00+01:00",
        "dateModified": f"{article['date_modified']}T08:00:00+01:00",
        "author": {
            "@type": "Person",
            "name": article["author"],
            "jobTitle": article.get("author_role", "Author")
        },
        "publisher": {
            "@type": "Organization",
            "name": "Academic Comeback",
            "url": SITE_URL,
            "logo": {
                "@type": "ImageObject",
                "url": f"{SITE_URL}/assets/images/logo.svg"
            }
        },
        "mainEntityOfPage": canonical_url,
        "inLanguage": "en-NG"
    }

    graph = [breadcrumbs, blog_posting]

    # 3. FAQPage Schema if FAQ items exist
    if article.get("faq") and isinstance(article["faq"], list) and len(article["faq"]) > 0:
        faq_entities = []
        for item in article["faq"]:
            if isinstance(item, dict) and "question" in item and "answer" in item:
                faq_entities.append({
                    "@type": "Question",
                    "name": item["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": item["answer"]
                    }
                })
        if faq_entities:
            graph.append({
                "@type": "FAQPage",
                "mainEntity": faq_entities
            })

    schema_dict = {
        "@context": "https://schema.org",
        "@graph": graph
    }
    return json.dumps(schema_dict, indent=2, ensure_ascii=False)


# ── Dual Theme Components (Light & Dark) ────────────────────────────────────

THEME_HEAD_SCRIPT = """  <!-- Anti-flicker Theme Init -->
  <script>
    (function() {
      try {
        var saved = localStorage.getItem('academic_blog_theme');
        var preferred = saved || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', preferred);
      } catch(e) {}
    })();
  </script>"""

THEME_TOGGLE_HTML = """<button type="button" class="theme-toggle" id="theme-toggle" aria-label="Toggle light or dark theme" title="Toggle theme">
          <span class="theme-toggle__icon-wrap">
            <i class="bi bi-moon-stars-fill theme-toggle__moon" aria-hidden="true"></i>
            <i class="bi bi-sun-fill theme-toggle__sun" aria-hidden="true"></i>
          </span>
          <span class="theme-toggle__text">Theme</span>
        </button>"""

THEME_FOOTER_SCRIPT = """  <!-- Theme Toggle Controller -->
  <script>
    (function() {
      function updateToggleUI(theme) {
        var btn = document.getElementById('theme-toggle');
        if (!btn) return;
        var isDark = theme === 'dark';
        btn.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        btn.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        var text = btn.querySelector('.theme-toggle__text');
        if (text) text.textContent = isDark ? 'Light' : 'Dark';
      }

      var current = document.documentElement.getAttribute('data-theme') || 'light';
      updateToggleUI(current);

      var btn = document.getElementById('theme-toggle');
      if (btn) {
        btn.addEventListener('click', function() {
          var cur = document.documentElement.getAttribute('data-theme') || 'light';
          var target = cur === 'dark' ? 'light' : 'dark';
          document.documentElement.setAttribute('data-theme', target);
          try {
            localStorage.setItem('academic_blog_theme', target);
          } catch(e) {}
          updateToggleUI(target);
        });
      }

      if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
          try {
            if (!localStorage.getItem('academic_blog_theme')) {
              var newTheme = e.matches ? 'dark' : 'light';
              document.documentElement.setAttribute('data-theme', newTheme);
              updateToggleUI(newTheme);
            }
          } catch(e) {}
        });
      }

      // Make entire blog card clickable on tap or click
      document.addEventListener('click', function(e) {
        var card = e.target.closest('.blog-card');
        if (!card) return;
        // If clicking directly on an anchor or button, let native browser action occur
        if (e.target.closest('a') || e.target.closest('button')) return;
        var primaryLink = card.querySelector('.blog-card__title a') || card.querySelector('.blog-card__cta') || card.querySelector('.blog-card__link');
        if (primaryLink && primaryLink.href) {
          window.location.href = primaryLink.href;
        }
      });

      // Keyboard accessibility: Enter or Space opens focused card
      document.addEventListener('keydown', function(e) {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        var card = document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('blog-card') ? document.activeElement : null;
        if (!card) return;
        var primaryLink = card.querySelector('.blog-card__title a') || card.querySelector('.blog-card__cta') || card.querySelector('.blog-card__link');
        if (primaryLink && primaryLink.href) {
          e.preventDefault();
          window.location.href = primaryLink.href;
        }
      });
    })();
  </script>"""


def get_global_blog_header() -> str:
    return f"""
  <!-- Top Flagship Announcement Bar -->
  <div class="global-top-bar">
    <div class="global-top-bar__inner">
      <span class="global-top-bar__badge">🌟 FLAGSHIP SYSTEM</span>
      <span><strong>The Academic Comeback Package™:</strong> Complete 7-in-1 study, memory &amp; CGPA turnaround system for Nigerian students is live (<strong>₦2,000</strong>).</span>
      <a href="/academic-comeback-package" class="global-top-bar__cta">Claim For ₦2,000 &rarr;</a>
    </div>
  </div>

  <!-- Unified Global Site Header -->
  <header class="global-site-header">
    <div class="global-header-inner">
      <a href="/" class="global-brand">
        <img src="/assets/images/scale-logo-cutout.png" alt="Scale Group Logo" width="23" height="28">
        <span>SCALE GROUP</span>
        <span class="global-brand__badge">STUDY &amp; GUIDES</span>
      </a>

      <!-- Desktop Navigation -->
      <nav class="global-nav">
        <a href="/academic-comeback-package" class="global-nav__flagship">
          <span class="global-nav__flagship-dot"></span>
          <i class="bi bi-mortarboard-fill"></i> Academic Comeback (Flagship)
        </a>
        <a href="/#masterclasses" class="global-nav__link">30 Masterclasses</a>
        <a href="/blog/" class="global-nav__link" style="color: #fff;">201+ Free Guides</a>
        <a href="/library" class="global-nav__link">My Library</a>
        <a href="/?support=true" class="global-nav__link">Support</a>
        {THEME_TOGGLE_HTML}
      </nav>

      <!-- Mobile Action Items -->
      <div class="global-header-mobile-actions">
        {THEME_TOGGLE_HTML}
        <a href="/academic-comeback-package" class="global-nav__mobile-flagship">
          <i class="bi bi-mortarboard-fill"></i> Flagship (₦2,000)
        </a>
        <button class="global-nav__toggle" onclick="openGlobalDrawer()" aria-label="Open Navigation Menu">
          <i class="bi bi-list"></i>
        </button>
      </div>
    </div>
  </header>
"""


def get_global_blog_drawer() -> str:
    return """
<!-- Mobile Drawer Backdrop -->
<div class="global-drawer-backdrop" id="global-drawer-backdrop" onclick="closeGlobalDrawer()"></div>

<!-- Mobile Navigation Drawer -->
<aside class="global-drawer" id="global-drawer" aria-label="Mobile Navigation">
  <div class="drawer-header">
    <a href="/" class="global-brand" onclick="closeGlobalDrawer()">
      <img src="/assets/images/scale-logo-cutout.png" alt="Scale Group Logo" width="22" height="26">
      <span>SCALE GROUP</span>
    </a>
    <button class="drawer-close" onclick="closeGlobalDrawer()" aria-label="Close menu">
      <i class="bi bi-x-lg"></i>
    </button>
  </div>

  <!-- Flagship Highlight Card Inside Drawer -->
  <div class="drawer-flagship-card">
    <div class="drawer-flagship-tag">
      <i class="bi bi-award-fill"></i> FLAGSHIP OFFER
    </div>
    <div class="drawer-flagship-title">Academic Comeback Package</div>
    <div class="drawer-flagship-desc">7-Part complete study, memory &amp; CGPA turnaround system for Nigerian students.</div>
    <div class="drawer-flagship-price">
      <span class="drawer-flagship-old">₦20,000</span>
      <span class="drawer-flagship-new">₦2,000</span>
      <span class="drawer-flagship-discount">SAVE 90%</span>
    </div>
    <a href="/academic-comeback-package" class="drawer-flagship-btn" onclick="closeGlobalDrawer()">
      Claim Flagship Package &rarr;
    </a>
  </div>

  <!-- Navigation Links -->
  <div class="drawer-nav-group">
    <div class="drawer-group-title">EXPLORE PLATFORM</div>
    <a href="/" class="drawer-nav-item" onclick="closeGlobalDrawer()">
      <i class="bi bi-house-door-fill"></i> <span>Home (All Products)</span>
    </a>
    <a href="/academic-comeback-package" class="drawer-nav-item drawer-nav-item--highlight" onclick="closeGlobalDrawer()">
      <i class="bi bi-mortarboard-fill"></i> <span>Academic Comeback Package (₦2,000)</span>
    </a>
    <a href="/#masterclasses" class="drawer-nav-item" onclick="closeGlobalDrawer()">
      <i class="bi bi-collection-play-fill"></i> <span>30 Tactical Masterclasses</span>
    </a>
    <a href="/blog/" class="drawer-nav-item" onclick="closeGlobalDrawer()">
      <i class="bi bi-journal-richtext"></i> <span>201+ Free Campus Guides</span>
    </a>
  </div>

  <div class="drawer-nav-group">
    <div class="drawer-group-title">BUYER &amp; STUDENT TOOLS</div>
    <a href="/library" class="drawer-nav-item" onclick="closeGlobalDrawer()">
      <i class="bi bi-folder-check"></i> <span>My Download Library</span>
    </a>
    <a href="/affiliate/dashboard" class="drawer-nav-item" onclick="closeGlobalDrawer()">
      <i class="bi bi-wallet2" style="color:#4ade80;"></i> <span>Ambassador Program (Earn ₦3,000)</span>
    </a>
    <a href="/?support=true" class="drawer-nav-item">
      <i class="bi bi-headset"></i> <span>Order Lookup &amp; Support</span>
    </a>
  </div>

  <div class="drawer-footer">
    ⭐ 4.9/5 Rating · 4,200+ Readers · Paystack Secured<br>© 2026 Scale Group
  </div>
</aside>
<script src="/js/global-nav.js" defer></script>
"""


# ── HTML Templates & Layout ──────────────────────────────────────────────────

def render_article_page(article: Dict[str, Any], categories: List[Dict[str, Any]], related_articles: List[Dict[str, Any]]) -> str:
    """Renders complete, indexable, semantic SSR HTML for an article page."""
    canonical_url = f"{SITE_URL}/blog/{article['category']}/{article['slug']}"
    json_ld = generate_json_ld(article)
    category = get_category_by_slug(article["category"]) or categories[0]

    # Build Related Articles HTML
    related_html = ""
    for rel in related_articles[:3]:
        rel_url = f"/blog/{rel['category']}/{rel['slug']}"
        related_html += f"""
        <article class="blog-card" tabindex="0">
          <div class="blog-card__meta">
            <span class="blog-card__tag" style="color:{rel.get('category_color', '#d4a63a')}">{rel['category_name']}</span>
            <span class="blog-card__date">{rel['date_published']}</span>
          </div>
          <h4 class="blog-card__title"><a href="{rel_url}">{rel['title']}</a></h4>
          <p class="blog-card__desc">{rel['description']}</p>
          <a href="{rel_url}" class="blog-card__link">Read Guide &rarr;</a>
        </article>
        """

    # Categories navigation pills
    cat_nav_html = ""
    for cat in categories:
        active_cls = " active" if cat["slug"] == article["category"] else ""
        cat_nav_html += f'<a href="/blog/{cat["slug"]}/" class="cat-pill{active_cls}"><i class="bi {cat["icon"]}"></i> {cat["name"]}</a>'

    featured_img = article.get("featured_image", "")
    if not featured_img or "bookcover.webp" in featured_img:
        social_img = f"{SITE_URL}/assets/images/scale-logo-512.png"
        hero_figure_html = ""
    else:
        social_img = f"{SITE_URL}{featured_img}" if featured_img.startswith("/") else featured_img
        hero_figure_html = f"""
      <!-- Featured Image -->
      <figure class="article-hero-media">
        <img src="{featured_img}" alt="{article['featured_image_alt']}" width="800" height="420" loading="eager" fetchpriority="high">
        <figcaption>{article['featured_image_alt']}</figcaption>
      </figure>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{article['title']} | Academic Comeback</title>
  <meta name="description" content="{article['description']}">
  <link rel="canonical" href="{canonical_url}">
  <link rel="icon" href="/favicon.ico">
  <meta name="robots" content="index, follow">

  <!-- Open Graph -->
  <meta property="og:type" content="article">
  <meta property="og:title" content="{article['title']}">
  <meta property="og:description" content="{article['description']}">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:image" content="{social_img}">
  <meta property="og:site_name" content="Academic Comeback">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{article['title']}">
  <meta name="twitter:description" content="{article['description']}">
  <meta name="twitter:image" content="{social_img}">

  <!-- Fonts & Styles -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Manrope:wght@400;500;600;700;800&display=swap">
  <link rel="stylesheet" href="https://api.fontshare.com/v2/css?f[]=clash-display@500,600,700&display=swap">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  
{THEME_HEAD_SCRIPT}
  <link rel="stylesheet" href="/css/main.css?v=4">
  <link rel="stylesheet" href="/css/blog.css?v=6">

  <!-- Structured Data JSON-LD -->
  <script type="application/ld+json">
{json_ld}
  </script>
</head>
<body class="blog-body">

{get_global_blog_header()}

  <!-- Categories Sub-Nav -->
  <div class="cat-bar">
    <div class="blog-container cat-bar__inner">
      <a href="/blog/" class="cat-pill"><i class="bi bi-grid-fill"></i> All Topics</a>
      {cat_nav_html}
    </div>
  </div>

  <!-- Main Article Layout -->
  <main class="blog-container blog-article-layout">
    <article class="article-content">
      
      <!-- Breadcrumbs -->
      <nav class="breadcrumbs" aria-label="Breadcrumb">
        <ol>
          <li><a href="/">Home</a></li>
          <li><i class="bi bi-chevron-right"></i></li>
          <li><a href="/blog/">Blog</a></li>
          <li><i class="bi bi-chevron-right"></i></li>
          <li><a href="/blog/{article['category']}/">{article['category_name']}</a></li>
          <li><i class="bi bi-chevron-right"></i></li>
          <li aria-current="page">{article['title']}</li>
        </ol>
      </nav>

      <!-- Article Header -->
      <header class="article-header">
        <div class="article-meta">
          <a href="/blog/{article['category']}/" class="article-category-badge" style="background:{category.get('bg_color', '#fef3c7')}; color:{category.get('color', '#b45309')}; border-color:{category.get('border_color', '#fde68a')};">
            <i class="bi {category['icon']}"></i> {article['category_name']}
          </a>
          <span class="article-meta__item"><i class="bi bi-calendar3"></i> {article['date_published']}</span>
          <span class="article-meta__item"><i class="bi bi-clock"></i> {article['read_time']}</span>
        </div>

        <h1 class="article-title">{article['title']}</h1>
        <p class="article-excerpt">{article['description']}</p>

        <!-- Author Byline -->
        <div class="author-byline">
          <div class="author-byline__avatar">
            <img src="/assets/images/author.webp" alt="{article['author']}" width="48" height="48" loading="lazy" onerror="this.src='/favicon.ico'">
          </div>
          <div class="author-byline__info">
            <span class="author-byline__name">{article['author']}</span>
            <span class="author-byline__role">{article['author_role']}</span>
          </div>
        </div>
      </header>

      <!-- Smart Audio Player Widget -->
      <div class="article-audio-player" id="article-audio-player" role="region" aria-label="Listen to article audio version">
        <div class="audio-player__main">
          <button class="audio-player__btn-play" id="audio-play-btn" type="button" aria-label="Listen to article">
            <i class="bi bi-play-fill" id="audio-play-icon"></i>
            <span id="audio-play-text">Listen to article</span>
          </button>
          <div class="audio-player__meta">
            <span class="audio-player__duration"><i class="bi bi-headphones"></i> {article['read_time']} listen</span>
            <span class="audio-player__status" id="audio-status-text">Click to play</span>
          </div>
        </div>
        <div class="audio-player__controls" id="audio-controls" style="display:none;">
          <div class="audio-player__progress-wrap">
            <div class="audio-player__progress-bar" id="audio-progress-bar" style="width: 0%;"></div>
          </div>
          <div class="audio-player__control-actions">
            <button class="audio-player__btn-ctrl" id="audio-prev-btn" type="button" title="Previous paragraph"><i class="bi bi-skip-backward-fill"></i></button>
            <button class="audio-player__btn-ctrl" id="audio-next-btn" type="button" title="Next paragraph"><i class="bi bi-skip-forward-fill"></i></button>
            <button class="audio-player__btn-ctrl audio-player__speed-btn" id="audio-speed-btn" type="button" title="Change speed">1.0x</button>
            <button class="audio-player__btn-ctrl" id="audio-stop-btn" type="button" title="Stop listening"><i class="bi bi-stop-fill"></i></button>
          </div>
        </div>
      </div>
{hero_figure_html}
      <!-- Article Body -->
      <div class="article-body">
        {article['body_html']}
      </div>

      <!-- Author Card Footer -->
      <div class="author-card">
        <div class="author-card__avatar">
          <img src="/assets/images/author.webp" alt="{article['author']}" width="72" height="72" loading="lazy" onerror="this.src='/favicon.ico'">
        </div>
        <div class="author-card__body">
          <span class="author-card__label">Written by</span>
          <h4 class="author-card__name">{article['author']}</h4>
          <p class="author-card__bio">Author of <em>Get Good at Hard Things</em> and founder of the Academic Comeback Package. Helping Nigerian university students master cognitive study systems, active recall, and high-performance degree execution.</p>
        </div>
      </div>

      <!-- ═════════════════════════════════════════════════════════════════
           READER DISCUSSION, TAKEAWAYS & TOPIC REQUEST ENGINE
           ═════════════════════════════════════════════════════════════════ -->
      <section class="blog-community-section" id="community">
        <div class="blog-community-tabs">
          <button type="button" class="comm-tab active" data-target="tab-comments" onclick="window.switchCommunityTab('tab-comments')">
            <i class="bi bi-chat-quote-fill"></i> Reader Takeaways &amp; Discussion (<span class="comment-count-badge">0</span>)
          </button>
          <button type="button" class="comm-tab" data-target="tab-topics" onclick="window.switchCommunityTab('tab-topics')">
            <i class="bi bi-lightbulb-fill"></i> Request a Topic for Itoya David
          </button>
        </div>

        <!-- Tab 1: Reader Comments & What I Liked -->
        <div id="tab-pane-comments" class="comm-tab-pane">
          <div class="comm-form-wrap">
            <div class="comm-form-header">
              <h3 class="comm-form-title">What Did You Like Most About This Guide?</h3>
              <p class="comm-form-sub">Share your favorite takeaway, a study technique you tested, or ask a question.</p>
            </div>

            <form onsubmit="window.submitBlogComment(event)">
              <input type="hidden" id="comment-slug" value="{article['slug']}">
              <input type="hidden" id="comment-article-title" value="{html.escape(article['title'], quote=True)}">

              <!-- Logged-in reader badge -->
              <div id="comment-author-badge" class="comment-author-badge" style="display:none;"></div>

              <!-- Guest email/name fields if not logged in -->
              <div id="comment-guest-fields" style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
                <div>
                  <label style="display:block; font-size:0.78rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;">Your Email <span style="color:#f87171">*</span></label>
                  <input type="email" id="guest-email" class="comment-input" placeholder="e.g. name@gmail.com">
                </div>
                <div>
                  <label style="display:block; font-size:0.78rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;">Name or Campus Alias</label>
                  <input type="text" id="guest-name" class="comment-input" placeholder="e.g. Chinedu (UNILAG)">
                </div>
              </div>

              <!-- What I Liked Selector -->
              <div style="margin-bottom:14px;">
                <label style="display:block; font-size:0.78rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;">What resonated most with you?</label>
                <select id="comment-what-liked" class="comment-select">
                  <option value="Active Recall & Spaced Repetition">Active Recall &amp; Spaced Repetition Protocol</option>
                  <option value="Actionable Exam Strategy">Actionable Exam Preparation Tactics</option>
                  <option value="Mathematical CGPA Breakdown">Mathematical CGPA Roadmap &amp; Calculation</option>
                  <option value="Hostel & Campus Survival Advice">Hostel &amp; Campus Survival Advice</option>
                  <option value="Mindset & Cognitive Stamina">Mindset &amp; Mental Discipline Shift</option>
                  <option value="Direct University Realism">Realistic Breakdown of Nigerian Lecturers</option>
                  <option value="Everything in this Guide">Everything in this Guide!</option>
                </select>
              </div>

              <!-- Comment Body -->
              <div style="margin-bottom:14px;">
                <label style="display:block; font-size:0.78rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;">Your Feedback / Question <span style="color:#f87171">*</span></label>
                <textarea id="comment-content" class="comment-textarea" required placeholder="Tell us how you study, what clicked for you, or ask a question about your semester..."></textarea>
              </div>

              <div id="comment-status" style="display:none; font-size:0.84rem; margin-bottom:12px;"></div>

              <button type="submit" id="comment-submit-btn" class="btn btn--gold" style="padding:10px 22px; font-size:0.88rem; font-weight:800;">
                <i class="bi bi-send-fill"></i> Post Takeaway &rarr;
              </button>
            </form>
          </div>

          <!-- Existing Comments List -->
          <div id="comments-list">
            <div style="text-align:center; padding:20px; color:#94a3b8;">Loading student discussion...</div>
          </div>
        </div>

        <!-- Tab 2: Topic Requests -->
        <div id="tab-pane-topics" class="comm-tab-pane" style="display:none;">
          <div class="comm-form-wrap">
            <div class="comm-form-header">
              <h3 class="comm-form-title">Have a Topic You'd Love Itoya David to Cover?</h3>
              <p class="comm-form-sub">Submit your specific academic, hostel, or campus challenge. The community upvotes, and we write deep-dive guides on the top requests.</p>
            </div>

            <form onsubmit="window.submitTopicRequest(event)">
              <div style="display:grid; grid-template-columns:2fr 1fr; gap:12px; margin-bottom:14px;">
                <div>
                  <label style="display:block; font-size:0.78rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;">Suggested Topic Title / Question <span style="color:#f87171">*</span></label>
                  <input type="text" id="topic-title" class="comment-input" required placeholder="e.g. How to recover when a lecturer fails your CA test...">
                </div>
                <div>
                  <label style="display:block; font-size:0.78rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;">Pillar Category</label>
                  <select id="topic-category" class="comment-select">
                    <option value="Academics">Academics</option>
                    <option value="Hostel & Accommodation">Hostel &amp; Accommodation</option>
                    <option value="Finances">Student Finances</option>
                    <option value="Mental Health">Mental Health</option>
                    <option value="Work & School">Work &amp; School</option>
                  </select>
                </div>
              </div>

              <!-- Topic email if guest -->
              <div id="topic-guest-fields" style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
                <div>
                  <label style="display:block; font-size:0.78rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;">Your Email (for notification when published) <span style="color:#f87171">*</span></label>
                  <input type="email" id="topic-guest-email" class="comment-input" placeholder="e.g. yourname@gmail.com">
                </div>
                <div>
                  <label style="display:block; font-size:0.78rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;">Your Name / University</label>
                  <input type="text" id="topic-guest-name" class="comment-input" placeholder="e.g. Tobi (FUTA)">
                </div>
              </div>

              <div style="margin-bottom:14px;">
                <label style="display:block; font-size:0.78rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;">Why does this matter to you? <span style="color:#f87171">*</span></label>
                <textarea id="topic-why" class="comment-textarea" required placeholder="Explain why students struggle with this on your campus..."></textarea>
              </div>

              <div id="topic-status" style="display:none; font-size:0.84rem; margin-bottom:12px;"></div>

              <button type="submit" id="topic-submit-btn" class="btn btn--gold" style="padding:10px 22px; font-size:0.88rem; font-weight:800;">
                <i class="bi bi-lightbulb-fill"></i> Submit Topic Request &rarr;
              </button>
            </form>
          </div>

          <!-- Community Roadmap Topics List with Upvoting -->
          <div style="margin-top:24px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
              <h4 style="color:#fff; font-size:1rem; font-weight:800; margin:0;">
                <i class="bi bi-fire" style="color:#f59e0b"></i> Student Topic Leaderboard (Upvote to Prioritize)
              </h4>
            </div>
            <div id="topics-list">
              <div style="text-align:center; padding:20px; color:#94a3b8;">Loading community roadmap...</div>
            </div>
          </div>
        </div>
      </section>

    </article>

    <!-- Sidebar / Related Articles -->
    <aside class="blog-sidebar">
      <div class="sidebar-sticky">
        
        <!-- Offer Card in Sidebar -->
        <div class="sidebar-cta-card">
          <span class="sidebar-cta-card__badge">Top Recommendation</span>
          <h4 class="sidebar-cta-card__title">Academic Comeback Package</h4>
          <p class="sidebar-cta-card__text">The complete 7-part digital learning system for Nigerian students. Turn poor grades around in 30 days.</p>
          <div class="sidebar-cta-card__price">₦2,000 <span>(₦20,000 Retail)</span></div>
          <a href="/academic-comeback-package" class="sidebar-cta-card__btn">Claim 90% Off Deal &rarr;</a>
        </div>

        <!-- Pillar Navigation -->
        <div class="sidebar-box">
          <h4 class="sidebar-box__title">Explore Topics</h4>
          <ul class="sidebar-category-list">
            {"".join(f'<li><a href="/blog/{c["slug"]}/"><i class="bi {c["icon"]}"></i> {c["name"]}</a></li>' for c in categories)}
          </ul>
        </div>

      </div>
    </aside>
  </main>

  <!-- Related Content Section -->
  <section class="related-section">
    <div class="blog-container">
      <div class="section-heading">
        <span class="section-tag">Next Steps</span>
        <h3 class="section-title">Related Study Guides &amp; Protocols</h3>
      </div>
      <div class="blog-grid">
        {related_html}
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="blog-footer">
    <div class="blog-container blog-footer__inner">
      <div class="blog-footer__brand">
        <span class="brand-text">SCALE GROUP</span>
        <p>Evidence-based study systems, active recall protocols, and campus survival strategies for Nigerian higher institutions.</p>
      </div>
      <div class="blog-footer__links">
        <a href="/">Home</a>
        <a href="/academic-comeback-package">Academic Comeback Package</a>
        <a href="/#masterclasses">30 Masterclasses</a>
        <a href="/blog/">All 201+ Guides</a>
        <a href="/library">My Library</a>
        <a href="/affiliate/dashboard">Ambassador Program</a>
      </div>
      <div class="blog-footer__copy">
        &copy; {datetime.now().year} Scale Group. All rights reserved.
      </div>
    </div>
  </footer>

  <script src="/js/blog-audio.js" defer></script>
  <script src="/js/blog-community.js" defer></script>
{THEME_FOOTER_SCRIPT}
{get_global_blog_drawer()}
</body>
</html>"""


def render_category_pillar_page(category: Dict[str, Any], articles: List[Dict[str, Any]], categories: List[Dict[str, Any]]) -> str:
    """Renders complete, indexable, semantic SSR HTML for a category pillar page."""
    canonical_url = f"{SITE_URL}/blog/{category['slug']}/"
    cat_articles = [a for a in articles if a["category"] == category["slug"]]

    # Build articles grid
    if cat_articles:
        articles_html = ""
        for art in cat_articles:
            art_url = f"/blog/{art['category']}/{art['slug']}"
            articles_html += f"""
            <article class="blog-card" tabindex="0">
              <div class="blog-card__meta">
                <span class="blog-card__tag" style="color:{category['color']}">{category['name']}</span>
                <span class="blog-card__date">{art['date_published']}</span>
                <span class="blog-card__read">{art['read_time']}</span>
              </div>
              <h3 class="blog-card__title"><a href="{art_url}">{art['title']}</a></h3>
              <p class="blog-card__desc">{art['description']}</p>
              <div class="blog-card__footer">
                <span class="blog-card__author"><i class="bi bi-person"></i> {art['author']}</span>
                <a href="{art_url}" class="blog-card__cta">Read Guide &rarr;</a>
              </div>
            </article>
            """
    else:
        articles_html = f"""
        <div class="empty-state">
          <i class="bi {category['icon']}"></i>
          <h3>Guides Incoming</h3>
          <p>We are currently finalizing tactical field guides for {category['name']}. Check back soon or explore our core system.</p>
          <a href="/academic-comeback-package" class="empty-state__btn">Explore Academic Comeback Package &rarr;</a>
        </div>
        """

    # Category pills
    cat_nav_html = ""
    for cat in categories:
        active_cls = " active" if cat["slug"] == category["slug"] else ""
        cat_nav_html += f'<a href="/blog/{cat["slug"]}/" class="cat-pill{active_cls}"><i class="bi {cat["icon"]}"></i> {cat["name"]}</a>'

    # Breadcrumb schema
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": f"{SITE_URL}/"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Blog",
                "item": f"{SITE_URL}/blog/"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": category["name"],
                "item": canonical_url
            }
        ]
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{category['name']} Guides &amp; Protocols | Academic Comeback</title>
  <meta name="description" content="{category['short_desc']}">
  <link rel="canonical" href="{canonical_url}">
  <link rel="icon" href="/favicon.ico">
  <meta name="robots" content="index, follow">

  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:title" content="{category['name']} Guides & Protocols">
  <meta property="og:description" content="{category['short_desc']}">
  <meta property="og:url" content="{canonical_url}">

  <!-- Fonts & Styles -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Manrope:wght@400;500;600;700;800&display=swap">
  <link rel="stylesheet" href="https://api.fontshare.com/v2/css?f[]=clash-display@500,600,700&display=swap">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  
{THEME_HEAD_SCRIPT}
  <link rel="stylesheet" href="/css/main.css?v=4">
  <link rel="stylesheet" href="/css/blog.css?v=6">

  <script type="application/ld+json">
{json_ld_dump(breadcrumb_schema)}
  </script>
</head>
<body class="blog-body">

  {get_global_blog_header()}

  <div class="cat-bar">
    <div class="blog-container cat-bar__inner">
      <a href="/blog/" class="cat-pill"><i class="bi bi-grid-fill"></i> All Topics</a>
      {cat_nav_html}
    </div>
  </div>

  <main class="blog-container pillar-hero">
    <!-- Breadcrumbs -->
    <nav class="breadcrumbs" aria-label="Breadcrumb">
      <ol>
        <li><a href="/">Home</a></li>
        <li><i class="bi bi-chevron-right"></i></li>
        <li><a href="/blog/">Blog</a></li>
        <li><i class="bi bi-chevron-right"></i></li>
        <li aria-current="page">{category['name']}</li>
      </ol>
    </nav>

    <div class="pillar-header">
      <span class="pillar-badge" style="background:{category.get('bg_color', '#fef3c7')}; color:{category.get('color', '#b45309')}; border: 1px solid {category.get('border_color', '#fde68a')};">
        <i class="bi {category['icon']}"></i> Category Pillar
      </span>
      <h1 class="pillar-title">{category['name']}</h1>
      <p class="pillar-intro">{category['intro']}</p>
    </div>

    <!-- Articles Grid -->
    <section class="pillar-articles">
      <div class="pillar-section-meta">
        <h2>Published Guides ({len(cat_articles)})</h2>
      </div>
      <div class="blog-grid">
        {articles_html}
      </div>
    </section>

    <!-- Relevant Offer Banner -->
    <div class="blog-cta-box" style="margin-top: 60px;">
      <div class="blog-cta-box__badge">Master Your Studies</div>
      <h3 class="blog-cta-box__title">Ready to Transform Your University Results?</h3>
      <p class="blog-cta-box__desc">Get access to all 7 core manuals, revision trackers, and exam panic checklists in the Academic Comeback Package.</p>
      <a href="/academic-comeback-package" class="blog-cta-box__btn">Claim Your Student Discount Now &rarr;</a>
    </div>
  </main>

  <footer class="blog-footer">
    <div class="blog-container blog-footer__inner">
      <div class="blog-footer__brand">
        <span class="brand-text">SCALE GROUP</span>
        <p>Evidence-based study systems, active recall protocols, and campus survival strategies for Nigerian higher institutions.</p>
      </div>
      <div class="blog-footer__links">
        <a href="/">Home</a>
        <a href="/academic-comeback-package">Academic Comeback Package</a>
        <a href="/#masterclasses">30 Masterclasses</a>
        <a href="/blog/">All 201+ Guides</a>
        <a href="/library">My Library</a>
        <a href="/affiliate/dashboard">Ambassador Program</a>
      </div>
      <div class="blog-footer__copy">
        &copy; {datetime.now().year} Scale Group. All rights reserved.
      </div>
    </div>
  </footer>

  <script src="/js/blog-community.js" defer></script>
{THEME_FOOTER_SCRIPT}
{get_global_blog_drawer()}
</body>
</html>"""


def render_blog_hub_page(articles: List[Dict[str, Any]], categories: List[Dict[str, Any]]) -> str:
    """Renders complete, indexable, semantic SSR HTML for the main /blog/ index."""
    canonical_url = f"{SITE_URL}/blog/"

    # Articles cards
    articles_html = ""
    for art in articles:
        art_url = f"/blog/{art['category']}/{art['slug']}"
        articles_html += f"""
        <article class="blog-card" tabindex="0">
          <div class="blog-card__meta">
            <span class="blog-card__tag" style="color:{art.get('category_color', '#d4a63a')}">{art['category_name']}</span>
            <span class="blog-card__date">{art['date_published']}</span>
            <span class="blog-card__read">{art['read_time']}</span>
          </div>
          <h3 class="blog-card__title"><a href="{art_url}">{art['title']}</a></h3>
          <p class="blog-card__desc">{art['description']}</p>
          <div class="blog-card__footer">
            <span class="blog-card__author"><i class="bi bi-person"></i> {art['author']}</span>
            <a href="{art_url}" class="blog-card__cta">Read Guide &rarr;</a>
          </div>
        </article>
        """

    # Category cards
    cat_cards_html = ""
    for cat in categories:
        count = sum(1 for a in articles if a["category"] == cat["slug"])
        cat_cards_html += f"""
        <a href="/blog/{cat['slug']}/" class="cat-card">
          <div class="cat-card__icon" style="background:{cat.get('bg_color', '#fef3c7')}; color:{cat.get('color', '#b45309')}; border: 1px solid {cat.get('border_color', '#fde68a')};">
            <i class="bi {cat['icon']}"></i>
          </div>
          <div class="cat-card__body">
            <h3 class="cat-card__title">{cat['name']}</h3>
            <p class="cat-card__desc">{cat['short_desc']}</p>
            <span class="cat-card__count">{count} published guides &rarr;</span>
          </div>
        </a>
        """

    # Category pills
    cat_nav_html = ""
    for cat in categories:
        cat_nav_html += f'<a href="/blog/{cat["slug"]}/" class="cat-pill"><i class="bi {cat["icon"]}"></i> {cat["name"]}</a>'

    # Hub Schema
    hub_schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": f"{SITE_URL}/"
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Blog",
                        "item": canonical_url
                    }
                ]
            },
            {
                "@type": "Blog",
                "name": "Academic Comeback Student Survival & Study Guides",
                "url": canonical_url,
                "description": "Evidence-based study systems, active recall protocols, and campus survival strategies for Nigerian higher institutions.",
                "publisher": {
                    "@type": "Organization",
                    "name": "Academic Comeback",
                    "url": f"{SITE_URL}/"
                }
            }
        ]
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>University Survival &amp; Academic Guides for Nigerian Students | Academic Comeback</title>
  <meta name="description" content="Tactical guides on CGPA recovery, active recall study systems, hostel living, student budgeting, and mental endurance for Nigerian university students.">
  <link rel="canonical" href="{canonical_url}">
  <link rel="icon" href="/favicon.ico">
  <meta name="robots" content="index, follow">

  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:title" content="University Survival & Academic Guides for Nigerian Students">
  <meta property="og:description" content="Tactical guides on CGPA recovery, active recall study systems, hostel living, student budgeting, and mental endurance.">
  <meta property="og:url" content="{canonical_url}">

  <!-- Fonts & Styles -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Manrope:wght@400;500;600;700;800&display=swap">
  <link rel="stylesheet" href="https://api.fontshare.com/v2/css?f[]=clash-display@500,600,700&display=swap">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  
{THEME_HEAD_SCRIPT}
  <link rel="stylesheet" href="/css/main.css?v=4">
  <link rel="stylesheet" href="/css/blog.css?v=6">

  <script type="application/ld+json">
{json_ld_dump(hub_schema)}
  </script>
</head>
<body class="blog-body">

  {get_global_blog_header()}

  <div class="cat-bar">
    <div class="blog-container cat-bar__inner">
      <a href="/blog/" class="cat-pill active"><i class="bi bi-grid-fill"></i> All Topics</a>
      {cat_nav_html}
    </div>
  </div>

  <main class="blog-container hub-main">
    <div class="hub-hero">
      <span class="section-tag">Campus Knowledge Base</span>
      <h1 class="hub-title">The Student Survival &amp; Academic Comeback Library</h1>
      <p class="hub-sub">Evidence-based study systems, active recall frameworks, and real-world campus survival strategies for Nigerian university students.</p>
    </div>

    <!-- Category Pillars Grid -->
    <section class="hub-categories">
      <h2 class="hub-section-heading">Browse by Pillar Category</h2>
      <div class="cat-grid">
        {cat_cards_html}
      </div>
    </section>

    <!-- Latest Articles -->
    <section class="hub-articles">
      <h2 class="hub-section-heading">Latest Published Guides</h2>
      <div class="blog-grid">
        {articles_html}
      </div>
    </section>

    <!-- Student Topic Request & Community Roadmap -->
    <section class="blog-community-section" id="community-topics" style="margin-top: 50px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
        <div>
          <span class="comm-badge"><i class="bi bi-lightbulb-fill"></i> COMMUNITY ROADMAP</span>
          <h2 style="color:#fff; font-size:1.4rem; font-weight:800; margin:6px 0 2px 0;">Request a Topic for Itoya David &amp; Scale Group</h2>
          <p style="color:#94a3b8; font-size:0.88rem; margin:0;">Upvote topics you want us to research next, or submit your specific campus challenge.</p>
        </div>
        <button type="button" class="btn btn--gold" onclick="window.openReaderLoginModal()" style="padding:10px 20px; font-size:0.85rem; font-weight:800;">
          <i class="bi bi-plus-circle"></i> Suggest a Topic &rarr;
        </button>
      </div>

      <!-- Topics List -->
      <div id="topics-list">
        <div style="text-align:center; padding:24px; color:#94a3b8;">Loading community roadmap...</div>
      </div>
    </section>

    <!-- Bottom CTA -->
    <div class="blog-cta-box" style="margin-top: 60px;">
      <div class="blog-cta-box__badge">Master Your Studies</div>
      <h3 class="blog-cta-box__title">Ready to Turn Your Academic Journey Around?</h3>
      <p class="blog-cta-box__desc">Get access to all 7 core manuals, revision trackers, and exam panic checklists in the Academic Comeback Package.</p>
      <a href="/academic-comeback-package" class="blog-cta-box__btn">Unlock The 7-Part System (₦2,000 Student Access) &rarr;</a>
    </div>
  </main>

  <footer class="blog-footer">
    <div class="blog-container blog-footer__inner">
      <div class="blog-footer__brand">
        <span class="brand-text">SCALE GROUP</span>
        <p>Evidence-based study systems, active recall protocols, and campus survival strategies for Nigerian higher institutions.</p>
      </div>
      <div class="blog-footer__links">
        <a href="/">Home</a>
        <a href="/academic-comeback-package">Academic Comeback Package</a>
        <a href="/#masterclasses">30 Masterclasses</a>
        <a href="/blog/">All 201+ Guides</a>
        <a href="/library">My Library</a>
        <a href="/affiliate/dashboard">Ambassador Program</a>
      </div>
      <div class="blog-footer__copy">
        &copy; {datetime.now().year} Scale Group. All rights reserved.
      </div>
    </div>
  </footer>

  <script src="/js/blog-community.js" defer></script>
{THEME_FOOTER_SCRIPT}
{get_global_blog_drawer()}
</body>
</html>"""


def json_ld_dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


# ── Static Generation & Sitemap Generation ───────────────────────────────────

def generate_sitemap_xml(articles: List[Dict[str, Any]], categories: List[Dict[str, Any]]) -> str:
    """
    Generates a dynamic, fully valid XML sitemap including:
    - Root and primary landing pages
    - Main /blog/ hub
    - All 5 category pillar pages (/blog/{cat}/)
    - All published article pages (/blog/{cat}/{slug})
    """
    today_iso = datetime.now().strftime("%Y-%m-%d")

    urls = [
        {"loc": f"{SITE_URL}/", "priority": "1.0", "changefreq": "weekly", "lastmod": today_iso},
        {"loc": f"{SITE_URL}/academic-comeback-package", "priority": "0.95", "changefreq": "weekly", "lastmod": today_iso},
        {"loc": f"{SITE_URL}/blog/", "priority": "0.9", "changefreq": "daily", "lastmod": today_iso},
        {"loc": f"{SITE_URL}/llms.txt", "priority": "0.85", "changefreq": "weekly", "lastmod": today_iso},
        {"loc": f"{SITE_URL}/pricing.md", "priority": "0.85", "changefreq": "weekly", "lastmod": today_iso},
    ]

    # Category pillar pages
    for cat in categories:
        urls.append({
            "loc": f"{SITE_URL}/blog/{cat['slug']}/",
            "priority": "0.85",
            "changefreq": "daily",
            "lastmod": today_iso
        })

    # Published articles
    for art in articles:
        if art.get("status") == "published":
            art_lastmod = art.get("date_modified") or art.get("date_published") or today_iso
            urls.append({
                "loc": f"{SITE_URL}/blog/{art['category']}/{art['slug']}",
                "priority": "0.8",
                "changefreq": "weekly",
                "lastmod": art_lastmod
            })

    # Other pages
    urls.extend([
        {"loc": f"{SITE_URL}/affiliate/register", "priority": "0.6", "changefreq": "monthly", "lastmod": today_iso},
        {"loc": f"{SITE_URL}/us", "priority": "0.7", "changefreq": "weekly", "lastmod": today_iso},
    ])

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for u in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{u['loc']}</loc>")
        xml_lines.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        xml_lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{u['priority']}</priority>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")
    xml_lines.append("")

    return "\n".join(xml_lines)


def build_all_static_blog_pages() -> Dict[str, Any]:
    """
    Compiles all Markdown articles into static, fully crawlable HTML files
    and auto-updates /sitemap.xml.
    """
    categories = get_categories()
    all_articles = get_all_articles(include_drafts=True)
    published_articles = [a for a in all_articles if a["status"] == "published"]

    # 1. Main Blog Hub -> frontend/blog/index.html
    BLOG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hub_html = render_blog_hub_page(published_articles, categories)
    with open(BLOG_OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(hub_html)

    # 2. Category Pillar Pages -> frontend/blog/{category}/index.html
    for cat in categories:
        cat_dir = BLOG_OUTPUT_DIR / cat["slug"]
        cat_dir.mkdir(parents=True, exist_ok=True)
        cat_html = render_category_pillar_page(cat, published_articles, categories)
        with open(cat_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(cat_html)

    # 3. Individual Article Pages -> frontend/blog/{category}/{slug}/index.html AND {slug}.html
    built_count = 0
    for art in published_articles:
        art_dir = BLOG_OUTPUT_DIR / art["category"] / art["slug"]
        art_dir.mkdir(parents=True, exist_ok=True)

        # Related articles
        related = [
            a for a in published_articles
            if a["slug"] != art["slug"] and (a["category"] == art["category"] or True)
        ]

        art_html = render_article_page(art, categories, related)
        with open(art_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(art_html)

        # Also write {slug}.html in the category dir for direct route fallback
        with open(BLOG_OUTPUT_DIR / art["category"] / f"{art['slug']}.html", "w", encoding="utf-8") as f:
            f.write(art_html)

        built_count += 1

    # 4. Generate & Save sitemap.xml
    sitemap_xml = generate_sitemap_xml(published_articles, categories)
    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    return {
        "status": "success",
        "categories_count": len(categories),
        "published_articles": len(published_articles),
        "draft_articles": len(all_articles) - len(published_articles),
        "built_pages": built_count,
        "sitemap_updated": True
    }


def save_article_markdown(article_data: Dict[str, Any]) -> str:
    """
    Saves or updates a Markdown article in content/articles/{slug}.md
    and triggers static regeneration.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", article_data.get("slug", "").lower()).strip("-")
    if not slug:
        raise ValueError("Article slug is required")

    file_path = ARTICLES_DIR / f"{slug}.md"

    # Build frontmatter
    faq_yaml = ""
    if article_data.get("faq"):
        faq_yaml = "faq:\n"
        for item in article_data["faq"]:
            q = item.get("question", "").replace('"', '\\"')
            a = item.get("answer", "").replace('"', '\\"')
            faq_yaml += f'  - question: "{q}"\n'
            faq_yaml += f'    answer: "{a}"\n'

    safe_title = str(article_data.get('title', '')).replace('"', '\\"')
    safe_description = str(article_data.get('description', '')).replace('"', '\\"')
    safe_author = str(article_data.get('author', 'Itoya David')).replace('"', '\\"')
    safe_author_role = str(article_data.get('author_role', 'Academic Strategist & Founder')).replace('"', '\\"')
    safe_image_alt = str(article_data.get('featured_image_alt', article_data.get('title', ''))).replace('"', '\\"')

    frontmatter = f"""---
title: "{safe_title}"
description: "{safe_description}"
slug: "{slug}"
category: "{article_data.get('category', 'academics')}"
author: "{safe_author}"
author_role: "{safe_author_role}"
date_published: "{article_data.get('date_published', datetime.now().strftime('%Y-%m-%d'))}"
date_modified: "{datetime.now().strftime('%Y-%m-%d')}"
status: "{article_data.get('status', 'draft')}"
read_time: "{article_data.get('read_time', '5 min read')}"
featured_image: "{article_data.get('featured_image', '')}"
featured_image_alt: "{safe_image_alt}"
{faq_yaml}---

{article_data.get('content', '').strip()}
"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)

    # Automatically recompile static pages & sitemap
    build_all_static_blog_pages()

    return slug


def delete_article_file(slug: str) -> bool:
    """Deletes an article file and rebuilds static files."""
    file_path = ARTICLES_DIR / f"{slug}.md"
    if file_path.exists():
        file_path.unlink()
        build_all_static_blog_pages()
        return True
    return False
