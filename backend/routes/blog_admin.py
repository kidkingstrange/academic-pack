"""
Admin API Router for Blog & Content CMS.
Enables creating, editing, publishing, deleting, and rebuilding
blog articles without touching code.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from ..middleware.auth import require_admin
from ..services.blog_service import (
    get_all_articles,
    get_article_by_slug,
    get_categories,
    save_article_markdown,
    delete_article_file,
    build_all_static_blog_pages
)

router = APIRouter(prefix="/api/admin/blog", tags=["admin-blog"])


class FAQItem(BaseModel):
    question: str
    answer: str


class ArticleSaveRequest(BaseModel):
    title: str = Field(..., min_length=3)
    slug: str = Field(..., min_length=2)
    category: str
    description: str
    author: Optional[str] = "Itoya David"
    author_role: Optional[str] = "Academic Strategist & Founder"
    date_published: Optional[str] = None
    status: str = Field("draft", pattern="^(draft|published)$")
    read_time: Optional[str] = "5 min read"
    featured_image: Optional[str] = ""
    featured_image_alt: Optional[str] = None
    faq: Optional[List[FAQItem]] = []
    content: str


@router.get("/categories")
async def list_categories(_admin=Depends(require_admin)):
    """Returns available blog categories."""
    return {"categories": get_categories()}


@router.get("/articles")
async def list_articles(_admin=Depends(require_admin)):
    """Returns all articles (both draft and published)."""
    articles = get_all_articles(include_drafts=True)
    summary = []
    for a in articles:
        summary.append({
            "slug": a["slug"],
            "title": a["title"],
            "category": a["category"],
            "category_name": a["category_name"],
            "status": a["status"],
            "author": a["author"],
            "date_published": a["date_published"],
            "read_time": a["read_time"],
            "url": f"/blog/{a['category']}/{a['slug']}" if a["status"] == "published" else None
        })
    return {"articles": summary, "total": len(summary)}


@router.get("/articles/{slug}")
async def get_article(slug: str, _admin=Depends(require_admin)):
    """Returns full article details for editing in the CMS."""
    article = get_article_by_slug(slug, include_drafts=True)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"article": article}


@router.post("/articles")
async def save_article(body: ArticleSaveRequest, _admin=Depends(require_admin)):
    """Saves or updates an article in content/articles/{slug}.md and recompiles static files."""
    try:
        faq_dicts = [{"question": f.question, "answer": f.answer} for f in (body.faq or [])]
        data = {
            "title": body.title,
            "slug": body.slug,
            "category": body.category,
            "description": body.description,
            "author": body.author,
            "author_role": body.author_role,
            "date_published": body.date_published,
            "status": body.status,
            "read_time": body.read_time,
            "featured_image": body.featured_image,
            "featured_image_alt": body.featured_image_alt or body.title,
            "faq": faq_dicts,
            "content": body.content
        }
        saved_slug = save_article_markdown(data)
        return {
            "status": "success",
            "slug": saved_slug,
            "message": f"Article '{body.title}' saved successfully as {body.status}."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save article: {str(e)}")


@router.delete("/articles/{slug}")
async def delete_article(slug: str, _admin=Depends(require_admin)):
    """Deletes an article file and updates static blog pages & sitemap."""
    success = delete_article_file(slug)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found or could not be deleted")
    return {"status": "success", "message": f"Article '{slug}' deleted."}


@router.post("/rebuild")
async def rebuild_blog(_admin=Depends(require_admin)):
    """Manually triggers a full rebuild of all static blog pages and sitemap.xml."""
    result = build_all_static_blog_pages()
    return {"status": "success", "result": result}
