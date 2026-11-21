#!/usr/bin/env python3
"""
Blog Content Migration Script: Static HTML to Next.js JSON/ISR Engine.
Parses all 400+ legacy static HTML blog articles in `frontend/blog/`,
extracts structured metadata (Schema.org JSON-LD, SEO tags, FAQs, article content),
and outputs them into `apps/website/data/blog/` for static generation (ISR).
"""

import os
import re
import json
import glob
from pathlib import Path
from html.parser import HTMLParser

BASE_DIR = Path(__file__).resolve().parent.parent
BLOG_DIR = BASE_DIR / "frontend" / "blog"
TARGET_DIR = BASE_DIR / "apps" / "website" / "data" / "blog"
POSTS_TARGET_DIR = TARGET_DIR / "posts"

CATEGORY_NAMES = {
    "academics": "Academics & Study Systems",
    "balancing-work-and-school": "Balancing Work & School",
    "finances": "Student Finances & Budgeting",
    "hostel-and-accommodation": "Hostel & Accommodation",
    "mental-health": "Mental Health & Stress Management"
}

def clean_html_content(raw_html: str) -> str:
    """Cleans up internal links and legacy relative asset paths in content."""
    cleaned = raw_html
    # Replace legacy relative asset links with absolute or modern public paths
    cleaned = re.sub(r'href="https://academic-pack\.onrender\.com/([^"]*)"', r'href="/\1"', cleaned)
    cleaned = re.sub(r'src="https://academic-pack\.onrender\.com/([^"]*)"', r'src="/\1"', cleaned)
    return cleaned.strip()

def parse_html_post(file_path: Path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    slug = file_path.stem
    category = file_path.parent.name

    # Skip index pages
    if slug == "index" or slug == "blog":
        return None

    # Title
    title = slug.replace("-", " ").title()
    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if title_match:
        full_title = title_match.group(1).strip()
        # Clean up suffix like ' | Academic Comeback'
        title = full_title.split("|")[0].strip()

    # Meta description
    description = ""
    desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE | re.DOTALL)
    if desc_match:
        description = desc_match.group(1).strip()
    else:
        og_desc = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE | re.DOTALL)
        if og_desc:
            description = og_desc.group(1).strip()

    # Canonical
    canonical = f"/blog/{category}/{slug}"
    canonical_match = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']', html, re.IGNORECASE | re.DOTALL)
    if canonical_match:
        canonical = canonical_match.group(1).strip()

    # Image
    image = f"/assets/images/blog/{slug}.webp"
    image_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE | re.DOTALL)
    if image_match:
        image = image_match.group(1).strip()

    # JSON-LD extraction
    date_published = "2026-09-26T08:00:00+01:00"
    date_modified = "2026-09-26T08:00:00+01:00"
    author_name = "Itoya David"
    faqs = []

    json_ld_matches = re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html, re.IGNORECASE | re.DOTALL)
    for ld_text in json_ld_matches:
        try:
            ld = json.loads(ld_text.strip())
            graph = ld.get("@graph", [ld]) if isinstance(ld, dict) else []
            for node in graph:
                if not isinstance(node, dict):
                    continue
                node_type = node.get("@type")
                if node_type in ("BlogPosting", "Article", "NewsArticle"):
                    if node.get("datePublished"):
                        date_published = node["datePublished"]
                    if node.get("dateModified"):
                        date_modified = node["dateModified"]
                    if isinstance(node.get("author"), dict) and node["author"].get("name"):
                        author_name = node["author"]["name"]
                    elif isinstance(node.get("author"), str):
                        author_name = node["author"]
                elif node_type == "FAQPage":
                    main_entity = node.get("mainEntity", [])
                    for q in main_entity:
                        if isinstance(q, dict) and "name" in q and "acceptedAnswer" in q:
                            ans_text = q["acceptedAnswer"].get("text", "")
                            faqs.append({
                                "question": q["name"],
                                "answer": ans_text
                            })
        except Exception:
            pass

    # Extract article body HTML
    content_html = ""
    # Look for <article class="article-content">...</article> or <article>...</article>
    article_match = re.search(r'<article[^>]*class=["\'][^"\']*article-content[^"\']*["\'][^>]*>(.*?)</article>', html, re.IGNORECASE | re.DOTALL)
    if not article_match:
        article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.IGNORECASE | re.DOTALL)

    if article_match:
        content_html = clean_html_content(article_match.group(1))
    else:
        # Fallback to <main>
        main_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.IGNORECASE | re.DOTALL)
        if main_match:
            content_html = clean_html_content(main_match.group(1))

    # Calculate estimated reading time
    words = len(re.findall(r'\w+', content_html))
    reading_time_mins = max(3, round(words / 200))

    return {
        "slug": slug,
        "category": category,
        "categoryName": CATEGORY_NAMES.get(category, category.replace("-", " ").title()),
        "title": title,
        "description": description,
        "canonical": canonical,
        "image": image,
        "datePublished": date_published,
        "dateModified": date_modified,
        "author": author_name,
        "readingTime": f"{reading_time_mins} min read",
        "faqs": faqs,
        "contentHtml": content_html
    }

def main():
    print("Starting Blog Content Migration from frontend/blog to apps/website/data/blog...")
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    POSTS_TARGET_DIR.mkdir(parents=True, exist_ok=True)

    categories = [d for d in BLOG_DIR.iterdir() if d.is_dir()]
    all_manifest = []

    total_migrated = 0
    for cat_dir in categories:
        cat_name = cat_dir.name
        cat_target = POSTS_TARGET_DIR / cat_name
        cat_target.mkdir(parents=True, exist_ok=True)

        html_files = list(cat_dir.glob("*.html"))
        print(f"Processing category '{cat_name}' ({len(html_files)} files)...")

        for html_file in html_files:
            post_data = parse_html_post(html_file)
            if not post_data:
                continue

            # Save individual JSON post file
            out_file = cat_target / f"{post_data['slug']}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(post_data, f, ensure_ascii=False, indent=2)

            # Strip bulky contentHtml for the fast manifest
            manifest_entry = {k: v for k, v in post_data.items() if k != "contentHtml"}
            all_manifest.append(manifest_entry)
            total_migrated += 1

    # Write master manifest
    manifest_file = TARGET_DIR / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(all_manifest, f, ensure_ascii=False, indent=2)

    print(f"Migration Complete! Successfully migrated {total_migrated} articles across {len(categories)} categories.")
    print(f"Master manifest written to: {manifest_file} ({len(all_manifest)} entries).")

if __name__ == "__main__":
    main()
