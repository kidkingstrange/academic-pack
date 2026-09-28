"""
Public Blog Router for Academic Comeback.
Serves server-side rendered, indexable HTML pages for:
- /blog/ (Main Hub)
- /blog/{category}/ (Pillar Page)
- /blog/{category}/{slug} (Article Page)
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from backend.services.blog_service import (
    get_categories,
    get_category_by_slug,
    get_all_articles,
    get_article_by_slug,
    render_blog_hub_page,
    render_category_pillar_page,
    render_article_page,
    BLOG_OUTPUT_DIR
)

router = APIRouter(prefix="/blog", tags=["blog"])


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_blog_hub():
    """Serves the main blog hub page with complete raw HTML."""
    static_file = BLOG_OUTPUT_DIR / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file), media_type="text/html; charset=utf-8")

    categories = get_categories()
    articles = get_all_articles(include_drafts=False)
    html = render_blog_hub_page(articles, categories)
    return HTMLResponse(content=html, status_code=200)


@router.get("/{category}", response_class=HTMLResponse, include_in_schema=False)
@router.get("/{category}/", response_class=HTMLResponse, include_in_schema=False)
async def serve_category_pillar(category: str):
    """Serves a category pillar page with complete raw HTML."""
    cat_obj = get_category_by_slug(category)
    if not cat_obj:
        raise HTTPException(status_code=404, detail="Category not found")

    static_file = BLOG_OUTPUT_DIR / category / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file), media_type="text/html; charset=utf-8")

    categories = get_categories()
    articles = get_all_articles(include_drafts=False)
    html = render_category_pillar_page(cat_obj, articles, categories)
    return HTMLResponse(content=html, status_code=200)


@router.get("/{category}/{slug}", response_class=HTMLResponse, include_in_schema=False)
@router.get("/{category}/{slug}/", response_class=HTMLResponse, include_in_schema=False)
async def serve_article_page(category: str, slug: str):
    """Serves an individual article page with complete raw HTML, schema, and meta tags."""
    cat_obj = get_category_by_slug(category)
    if not cat_obj:
        raise HTTPException(status_code=404, detail="Category not found")

    slug = slug.strip("/")
    # Check for compiled static file
    static_file = BLOG_OUTPUT_DIR / category / slug / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file), media_type="text/html; charset=utf-8")

    direct_file = BLOG_OUTPUT_DIR / category / f"{slug}.html"
    if direct_file.exists():
        return FileResponse(str(direct_file), media_type="text/html; charset=utf-8")

    # On-demand SSR
    article = get_article_by_slug(slug, include_drafts=False)
    if not article or article["category"] != category:
        raise HTTPException(status_code=404, detail="Article not found")

    categories = get_categories()
    all_published = get_all_articles(include_drafts=False)
    related = [a for a in all_published if a["slug"] != slug]

    html = render_article_page(article, categories, related)
    return HTMLResponse(content=html, status_code=200)
