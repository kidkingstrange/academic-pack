"""
Unit and integration tests for all 12 canonical books, including the 4 new additions:
- How to Close High-Paying Clients in the DMs
- How to Do Your Ideas
- What to Do After a Breakup
- What To Do When Your Boss Is Angry With You
"""
import pytest
from pathlib import Path
from backend.utils.canonical_products import (
    CANONICAL_PRODUCTS,
    get_canonical_product,
    get_canonical_price
)
from backend.utils.product_delivery import resolve_product_pdf_path


def test_canonical_catalog_integrity():
    assert len(CANONICAL_PRODUCTS) == 12
    orders = [p["order"] for p in CANONICAL_PRODUCTS]
    assert orders == list(range(1, 13))

    slugs = [p["slug"] for p in CANONICAL_PRODUCTS]
    assert len(set(slugs)) == 12, "All slugs must be unique"


@pytest.mark.parametrize("p", CANONICAL_PRODUCTS)
def test_all_canonical_products_resolve_existing_pdfs(p):
    resolved = resolve_product_pdf_path(p)
    assert resolved is not None, f"PDF path could not be resolved for {p['title']}"
    assert resolved.exists(), f"PDF file does not exist on disk: {resolved}"
    assert resolved.stat().st_size > 50000, f"PDF file looks empty or too small: {resolved}"


@pytest.mark.parametrize("p", CANONICAL_PRODUCTS)
def test_canonical_pricing_strictly_enforced(p):
    slug = p["slug"]
    title = p["title"]
    
    assert get_canonical_price(slug=slug, currency="NGN") == 5000.0
    assert get_canonical_price(slug=slug, currency="USD") == 15.0
    assert get_canonical_price(title=title, currency="NGN") == 5000.0
    assert get_canonical_price(title=title, currency="USD") == 15.0


def test_specific_new_books_resolution():
    new_slugs = [
        "how-to-close-high-paying-clients-in-the-dms",
        "how-to-do-your-ideas",
        "what-to-do-after-a-breakup",
        "what-to-do-when-your-boss-is-angry-with-you"
    ]
    for s in new_slugs:
        prod = get_canonical_product(slug=s)
        assert prod is not None, f"Failed to get product for slug {s}"
        assert prod["price_naira"] == 5000
        assert prod["price_usd"] == 15.0
        pdf = resolve_product_pdf_path(prod)
        assert pdf is not None and pdf.is_file()


@pytest.mark.asyncio
async def test_new_books_sales_pages_served_cleanly(client):
    pages = [
        ("/how-to-close-high-paying-clients-in-the-dms", "how-to-close-high-paying-clients-in-the-dms"),
        ("/clients-in-dm", "how-to-close-high-paying-clients-in-the-dms"),
        ("/how-to-do-your-ideas", "how-to-do-your-ideas"),
        ("/do-your-ideas", "how-to-do-your-ideas"),
        ("/what-to-do-after-a-breakup", "what-to-do-after-a-breakup"),
        ("/breakup", "what-to-do-after-a-breakup"),
        ("/what-to-do-when-your-boss-is-angry-with-you", "what-to-do-when-your-boss-is-angry-with-you"),
        ("/angry-boss", "what-to-do-when-your-boss-is-angry-with-you"),
        ("/quitting-the-handjob", "quitting-the-handjob"),
    ]
    for url, expected_slug in pages:
        res = await client.get(url)
        assert res.status_code == 200, f"Failed to serve {url}"
        html = res.text
        assert f"window.PRODUCT_SLUG = '{expected_slug}';" in html, f"Missing slug in {url}"
        assert "window.PRODUCT_PRICE = 5000;" in html, f"Missing price 5000 in {url}"
        assert "₦5,000" in html, f"Missing ₦5,000 price text in {url}"
        assert "checkout-modal" in html, f"Missing checkout modal in {url}"
        assert "main.js" not in html, f"Standalone page {url} should not load main.js (bundle countdown override)"
        assert "/assets/images/profileimg.webp" in html, f"Missing author photo in {url}"


@pytest.mark.asyncio
async def test_new_books_product_info_endpoint(client):
    slugs = [
        "how-to-close-high-paying-clients-in-the-dms",
        "how-to-do-your-ideas",
        "what-to-do-after-a-breakup",
        "what-to-do-when-your-boss-is-angry-with-you",
    ]
    for s in slugs:
        res = await client.get(f"/api/payments/product-info?slug={s}")
        assert res.status_code == 200, f"Product info failed for {s}"
        data = res.json()
        assert data["slug"] == s
        assert data["price_naira"] == 5000.0
        assert data["price_usd"] == 15.0
        assert data["title"] is not None

